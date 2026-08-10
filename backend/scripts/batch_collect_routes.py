"""
批量路线采集脚本 — 搜索+LLM 自动提取结构化路线数据
用法: python -m scripts.batch_collect_routes

原理：
  1. 对每条路线名执行 DuckDuckGo 搜索
  2. LLM 从搜索结果中提取结构化数据
  3. 保存到 JSON 文件，可手动审核后导入知识库
"""
import asyncio
import json
import os
import sys
import logging
from datetime import datetime

# 确保 backend 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ===== 待采集路线清单 =====
# 按省份组织的热门徒步路线（不在现有知识库中的）
ROUTES_TO_COLLECT = [
    # 浙江
    "莫干山徒步", "天目七尖穿越", "清凉峰徒步", "千八穿越", "雁荡山徒步",
    # 江苏
    "紫金山徒步", "苏州灵白线",
    # 福建
    "太姥山徒步", "鼓山徒步", "青云山徒步",
    # 广东
    "丹霞山徒步", "罗浮山徒步", "东西冲穿越", "七娘山徒步",
    # 广西
    "漓江徒步", "龙脊梯田徒步", "德天瀑布徒步",
    # 海南
    "五指山徒步", "尖峰岭徒步",
    # 湖南
    "张家界徒步", "衡山徒步", "崀山徒步", "八大公山徒步",
    # 湖北
    "恩施大峡谷徒步", "武当山徒步", "大别山徒步",
    # 河南
    "嵩山徒步", "云台山徒步", "老君山徒步", "白云山徒步",
    # 河北
    "小五台山徒步", "野三坡徒步", "白石山徒步",
    # 山东
    "泰山徒步", "崂山徒步", "蒙山徒步",
    # 山西
    "恒山徒步", "芦芽山徒步", "历山徒步",
    # 陕西
    "华山徒步", "终南山徒步", "翠华山徒步",
    # 甘肃
    "祁连山徒步", "马蹄寺徒步", "崆峒山徒步",
    # 青海
    "青海湖徒步", "年保玉则徒步", "阿尼玛卿转山", "茶卡盐湖徒步",
    # 宁夏
    "贺兰山徒步", "沙坡头徒步",
    # 辽宁
    "千山徒步", "凤凰山徒步",
    # 吉林
    "长白山徒步", "松花湖徒步",
    # 黑龙江
    "五大连池徒步", "镜泊湖徒步", "雪乡穿越",
    # 台湾
    "玉山徒步", "雪山徒步", "阿里山徒步", "太鲁阁徒步",
    # 重庆
    "武隆天坑徒步", "金佛山徒步", "仙女山徒步",
    # 贵州
    "黄果树徒步", "荔波茂兰徒步", "雷公山徒步", "万峰林徒步",
    # 江西
    "三清山徒步", "庐山徒步", "龙虎山徒步", "井冈山徒步",
    # 热门城市周边
    "香山徒步", "凤凰岭徒步", "阳台山徒步",
    "佘山徒步", "崇明岛徒步",
    "白云山徒步广州", "大夫山徒步",
    "梧桐山徒步", "大鹏半岛徒步",
]


async def collect_single_route(route_name: str, llm_service, sem: asyncio.Semaphore) -> dict | None:
    """采集单条路线数据"""
    async with sem:
        try:
            from app.services.search_service import search_route_info

            # 1. 搜索
            results = await search_route_info(route_name)
            if not results:
                logger.warning(f"  {route_name}: 搜索无结果")
                return None

            search_text = "\n\n".join([
                f"来源{i+1}: {r['title']}\n{r['body']}"
                for i, r in enumerate(results[:6])
            ])

            # 2. LLM 提取
            system = """你是徒步路线数据专家。从搜索结果中提取路线数据。四个数字字段必填！

```json
{
  "thinking": "分析",
  "output": {
    "name": "路线名",
    "distance_km": 数字(必填，不能为0),
    "elevation_gain_m": 数字(必填，不能为0),
    "max_elevation_m": 数字(必填，不能为0),
    "difficulty": "轻松/较易/中等/较难/困难/专业级",
    "duration_days": 数字(必填，不能为0),
    "terrain": "地形",
    "water_sources": "水源",
    "best_season": "最佳季节",
    "trailhead": "起点",
    "notes": "注意事项",
    "region": "省份",
    "data_source": "web_collection"
  }
}
```

规则：没有精确数据就根据路线所在区域、类似路线估算。distance_km>0!"""

            result = await llm_service.think(
                system_prompt=system,
                user_message=f"路线: {route_name}\n\n搜索结果:\n{search_text[:4000]}",
                output_format="json",
                max_tokens=1024,
                temperature=0.2,
            )

            if result.get("success") and result.get("json"):
                data = result["json"].get("output", result["json"])
                # 基本校验
                if data.get("distance_km", 0) > 0:
                    logger.info(f"  [OK] {route_name}: {data['distance_km']}km, {data['elevation_gain_m']}m, {data['difficulty']}")
                    return data
                else:
                    logger.warning(f"  [SKIP] {route_name}: distance_km=0, 数据不完整")
                    return None
            else:
                logger.warning(f"  [FAIL] {route_name}: LLM 提取失败")
                return None

        except Exception as e:
            logger.error(f"  [ERR] {route_name}: {e}")
            return None


async def main():
    from app.services.llm_service import get_llm_service

    llm = get_llm_service()
    if not llm.available:
        logger.error("LLM 不可用，无法采集")
        return

    sem = asyncio.Semaphore(3)  # 并发控制
    results = []
    failed = []

    logger.info(f"开始采集 {len(ROUTES_TO_COLLECT)} 条路线...\n")

    # 分批处理
    batch_size = 5
    for batch_start in range(0, len(ROUTES_TO_COLLECT), batch_size):
        batch = ROUTES_TO_COLLECT[batch_start:batch_start + batch_size]
        tasks = [collect_single_route(name, llm, sem) for name in batch]

        batch_results = await asyncio.gather(*tasks)

        for i, r in enumerate(batch_results):
            if r:
                results.append(r)
            else:
                failed.append(batch[i])

        # 批次间休息（避免搜索限流）
        if batch_start + batch_size < len(ROUTES_TO_COLLECT):
            await asyncio.sleep(2)
            logger.info(f"--- 进度 {min(batch_start+batch_size, len(ROUTES_TO_COLLECT))}/{len(ROUTES_TO_COLLECT)} ---")

    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "collected_routes.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "collected_at": datetime.now().isoformat(),
            "total": len(results),
            "routes": results,
            "failed": failed,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n===== 采集完成 =====")
    logger.info(f"成功: {len(results)} 条")
    logger.info(f"失败: {len(failed)} 条 ({', '.join(failed[:10])})")
    logger.info(f"保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
