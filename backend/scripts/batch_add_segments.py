"""
批量添加路线日程分段 — 对无 segments 的路线联网搜索+LLM提取每日分段
用法: python -m scripts.batch_add_segments

原理：
  1. 读取 route_analyst.py 的 KNOWN_ROUTES，跳过已有 segments 的
  2. 对每条路线执行 DuckDuckGo 搜索 "{路线名} 徒步 每天 行程 营地"
  3. LLM 从搜索结果中提取每日分段数据
  4. 每成功一条立即写入 route_segments.json（支持断点续传）
"""
import asyncio
import json
import os
import sys
import logging
from datetime import datetime

# 确保 backend 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEGMENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "route_segments.json")

# LLM Prompt: 提取每日分段
SYSTEM_PROMPT = """你是徒步路线数据专家。从搜索结果中提取每日徒步分段数据。

## 输出格式
```json
{
  "thinking": "分析搜索结果中关于每日行程的信息",
  "segments": [
    {
      "day": 1,
      "from": "起点名称(含海拔，如'沈子村600m')",
      "to": "终点名称(含海拔，如'金顶1918m')",
      "distance_km": 数字(当天距离，必填>0),
      "gain_m": 数字(当天爬升，必填>0),
      "terrain": "当天地形特征(15字内)",
      "water": "当天水源补给点",
      "highlights": "当天亮点/看点(15字内)",
      "risks": "当天主要风险(15字内)",
      "pace": "预计耗时和节奏建议(15字内)"
    }
  ]
}
```

## 规则（极其重要！）
1. segments 数组长度必须等于 duration_days
2. 每个 day 的 distance_km 和 gain_m 必须 > 0
3. 所有 segment 的 distance_km 之和 ≈ 路线总距离
4. 所有 segment 的 gain_m 之和 ≈ 路线总爬升
5. from/to 尽量包含海拔信息
6. 如果搜索结果没有详细分段→根据总距离/天数/地形合理推算
7. 单日徒步通常10-15km，高原路线8-12km
8. 只输出 JSON，不要 markdown 代码块"""


def load_segments() -> dict:
    """加载已有分段数据"""
    if os.path.exists(SEGMENTS_FILE):
        with open(SEGMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_segments(data: dict):
    """保存分段数据到 JSON 文件"""
    os.makedirs(os.path.dirname(SEGMENTS_FILE), exist_ok=True)
    with open(SEGMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def search_and_extract_segments(
    route_name: str,
    route_data: dict,
    llm_service,
    sem: asyncio.Semaphore,
) -> list[dict] | None:
    """搜索并提取单条路线的日程分段"""
    async with sem:
        try:
            from app.services.search_service import search_route_info

            duration = route_data.get("duration_days", 1)
            total_km = route_data.get("distance_km", 0)
            total_gain = route_data.get("elevation_gain_m", 0)

            # 搜索：用专门的分段搜索词
            # 先尝试搜索分段信息
            query = f"{route_name} 徒步 每天 行程 分段 营地 攻略"
            results = await search_route_info(route_name)

            # 再用分段专用词搜一次
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    extra = list(ddgs.text(query, max_results=4))
                    for r in extra:
                        results.append({
                            "title": r.get("title", ""),
                            "body": r.get("body", ""),
                            "href": r.get("href", ""),
                        })
            except Exception:
                pass

            if not results:
                logger.warning(f"  {route_name}: 搜索无结果")
                return None

            # 去重
            seen = set()
            unique = []
            for r in results:
                if r["href"] not in seen:
                    seen.add(r["href"])
                    unique.append(r)

            search_text = "\n\n".join([
                f"来源{i+1}: {r['title']}\n{r['body']}"
                for i, r in enumerate(unique[:8])
            ])

            # LLM 提取
            user_msg = (
                f"路线: {route_name}\n"
                f"总距离: {total_km}km\n"
                f"总爬升: {total_gain}m\n"
                f"天数: {duration}天\n"
                f"地形: {route_data.get('terrain', '未知')}\n"
                f"起点: {route_data.get('trailhead', '未知')}\n\n"
                f"搜索结果:\n{search_text[:5000]}"
            )

            result = await llm_service.think(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_msg,
                output_format="json",
                max_tokens=2048,
                temperature=0.2,
            )

            if result.get("success") and result.get("json"):
                data = result["json"]
                segments = data.get("segments", [])

                if not segments:
                    logger.warning(f"  {route_name}: LLM 返回空 segments")
                    return None

                # 校验
                valid = True
                for seg in segments:
                    if seg.get("distance_km", 0) <= 0 or seg.get("gain_m", 0) < 0:
                        valid = False
                        break
                    # 补齐缺失字段
                    seg.setdefault("day", len(segments) if not seg.get("day") else seg.get("day"))

                if not valid:
                    logger.warning(f"  {route_name}: segments 校验失败 (有 distance_km<=0)")
                    return None

                # 校验天数匹配（允许 ±1 天偏差）
                if abs(len(segments) - duration) > 1:
                    logger.warning(
                        f"  {route_name}: 天数不匹配 (expected {duration}, got {len(segments)})"
                    )

                total_seg_km = sum(s.get("distance_km", 0) for s in segments)
                logger.info(
                    f"  [OK] {route_name}: {len(segments)}天/{total_seg_km:.0f}km "
                    f"(路线标称{total_km}km/{duration}天)"
                )
                return segments

            else:
                error = result.get("error", "unknown")
                logger.warning(f"  [FAIL] {route_name}: LLM 失败 - {error}")
                return None

        except Exception as e:
            logger.error(f"  [ERR] {route_name}: {e}")
            return None


async def main():
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()
    if not llm.available:
        logger.error("LLM 不可用，无法运行")
        return

    # 加载路线知识库
    from app.agents.route_analyst import KNOWN_ROUTES

    # 加载已有分段
    current_segments = load_segments()
    logger.info(f"已有分段: {len(current_segments)} 条")

    # 找出需要处理的路线（无 segments 的）
    pending = []
    for name, data in KNOWN_ROUTES.items():
        if not isinstance(data, dict):
            continue
        # 跳过已有分段（无论是原始的还是 JSON 中的）
        if data.get("segments") or name in current_segments:
            continue
        pending.append((name, data))

    logger.info(f"知识库总数: {len(KNOWN_ROUTES)}")
    logger.info(f"待处理: {len(pending)} 条")
    logger.info(f"并发数: 3 | 批次间隔: 2s\n")

    if not pending:
        logger.info("所有路线都已有分段！")
        return

    sem = asyncio.Semaphore(3)
    success_count = 0
    fail_count = 0
    batch_size = 3

    for batch_start in range(0, len(pending), batch_size):
        batch = pending[batch_start:batch_start + batch_size]
        tasks = [
            search_and_extract_segments(name, data, llm, sem)
            for name, data in batch
        ]

        batch_results = await asyncio.gather(*tasks)

        # 立即保存成功的
        for i, segments in enumerate(batch_results):
            name = batch[i][0]
            if segments:
                current_segments[name] = segments
                save_segments(current_segments)
                success_count += 1
            else:
                fail_count += 1

        # 进度报告
        done = batch_start + len(batch)
        logger.info(
            f"--- 进度 {min(done, len(pending))}/{len(pending)} "
            f"({success_count}成功/{fail_count}失败) ---"
        )

        # 批次间休息
        if batch_start + batch_size < len(pending):
            await asyncio.sleep(2)

    # 最终报告
    logger.info(f"\n===== 批量分段升级完成 =====")
    logger.info(f"成功: {success_count} 条")
    logger.info(f"失败: {fail_count} 条")
    logger.info(f"分段文件: {SEGMENTS_FILE}")

    # 重新验证
    current_segments = load_segments()
    logger.info(f"route_segments.json 共 {len(current_segments)} 条分段数据")

    # 提示重新加载
    logger.info("\n⚠️  需要重启后端服务以加载新的分段数据")


if __name__ == "__main__":
    asyncio.run(main())
