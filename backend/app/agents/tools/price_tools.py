"""价格查询工具 — Agent 用于在各平台搜索装备价格"""
import logging

logger = logging.getLogger(__name__)


async def search_price(keyword: str, category: str = "equipment") -> dict:
    """
    搜索装备价格信息。

    在实际部署中替换为真实的电商/平台搜索 API。

    Args:
        keyword: 搜索关键词（装备名称）
        category: 装备类别

    Returns:
        价格比较数据
    """
    logger.info(f"[PriceSearch] 搜索 '{keyword}' 价格 (类别: {category})")

    # TODO: 集成真实价格搜索
    # 可使用淘宝/京东/拼多多 API，或爬取 REI/Amazon 价格

    return {
        "keyword": keyword,
        "category": category,
        "price_range": {
            "min": 0,
            "max": 0,
            "avg": 0,
            "currency": "CNY",
        },
        "platforms": [
            {"name": "淘宝", "price": 0, "url": ""},
            {"name": "京东", "price": 0, "url": ""},
            {"name": "REI", "price": 0, "url": ""},
        ],
        "note": "（实际部署时将返回真实价格数据）",
    }
