"""联网搜索服务 — 用于查找未知路线数据"""
import logging
import httpx

logger = logging.getLogger(__name__)

# 搜索关键词模板
SEARCH_TEMPLATES = [
    "{route} 徒步 路线 距离 攻略",
    "{route} 徒步 攻略 装备",
    "{route} 海拔 爬升 天数",
]


async def search_route_info(route_name: str) -> list[dict]:
    """
    搜索路线相关信息。使用 DuckDuckGo 免费搜索。

    Args:
        route_name: 路线名称

    Returns:
        [{"title": "...", "body": "...", "href": "..."}, ...]
    """
    results = []

    try:
        from ddgs import DDGS

        # 只用一个精简 query，避免 DDG 中文处理问题
        query = f"{route_name} 徒步攻略"

        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=6))
                for r in search_results:
                    results.append({
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "href": r.get("href", ""),
                    })
        except Exception as e:
            logger.warning(f"[Search] DDG 搜索失败: {e}，尝试备用方案...")
            results = await _fallback_search(route_name)

        # 去重
        seen = set()
        unique = []
        for r in results:
            if r["href"] not in seen:
                seen.add(r["href"])
                unique.append(r)

        logger.info(f"[Search] '{route_name}' 找到 {len(unique)} 条结果")
        return unique[:8]

    except Exception as e:
        logger.error(f"[Search] 搜索异常: {e}")
        return []


async def _fallback_search(route_name: str) -> list[dict]:
    """备用搜索：用 httpx 做简单的网页搜索"""
    results = []

    try:
        # Bing 搜索（中文支持好）
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 用 Bing 搜索
            resp = await client.get(
                "https://www.bing.com/search",
                params={"q": f"{route_name} 徒步 路线", "count": 10},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            if resp.status_code == 200:
                # 简单解析搜索结果
                import re
                html = resp.text
                # 提取 <h2> 标签内的标题
                titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
                # 提取描述片段
                snippets = re.findall(r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)

                for i in range(min(len(titles), len(snippets), 6)):
                    title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                    body = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                    if title and len(title) > 2:
                        results.append({
                            "title": title,
                            "body": body[:300],
                            "href": "",
                        })
    except Exception as e:
        logger.warning(f"[Search] 备用搜索失败: {e}")

    return results
