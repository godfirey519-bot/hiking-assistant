"""网络搜索工具 — Agent 用于在各户外平台搜索装备评测和数据"""
import logging

logger = logging.getLogger(__name__)

# 户外装备信息平台列表
OUTDOOR_PLATFORMS = [
    {"name": "8264户外资料网", "url": "https://www.8264.com", "type": "论坛/评测"},
    {"name": "两步路", "url": "https://www.2bulu.com", "type": "路线/社区"},
    {"name": "小红书", "url": "https://www.xiaohongshu.com", "type": "装备评测/种草"},
    {"name": "B站", "url": "https://www.bilibili.com", "type": "视频评测"},
    {"name": "REI", "url": "https://www.rei.com", "type": "装备购买/评测"},
    {"name": "OutdoorGearLab", "url": "https://www.outdoorgearlab.com", "type": "专业评测"},
    {"name": "Switchback Travel", "url": "https://www.switchbacktravel.com", "type": "专业评测"},
    {"name": "Section Hiker", "url": "https://sectionhiker.com", "type": "轻量化评测"},
]


async def search_web(query: str, search_type: str = "equipment", max_results: int = 5) -> list[dict]:
    """
    模拟网络搜索。在实际部署中替换为 Tavily/SerpAPI/Google Search API。

    返回结构化搜索结果供 Agent 分析使用。

    Args:
        query: 搜索关键词
        search_type: 搜索类型 (equipment/route/weather/price)
        max_results: 最大结果数

    Returns:
        搜索结果列表
    """
    logger.info(f"[WebSearch] 搜索 '{query}' (类型: {search_type})")

    # TODO: 集成真实搜索 API
    # from tavily import TavilyClient
    # client = TavilyClient(api_key="...")
    # results = client.search(query, max_results=max_results)

    return [{
        "title": f"关于 '{query}' 的搜索结果",
        "platform": "模拟数据",
        "snippet": "（实际部署时将返回真实搜索结果）",
        "url": "",
        "relevance_score": 1.0,
    }]
