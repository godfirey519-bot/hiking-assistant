"""天气服务 — Open-Meteo 免费天气 API 集成（无需 API Key）"""
import httpx
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Open-Meteo 天气代码 → 中文描述
WEATHER_CODES: dict[int, str] = {
    0: "晴天", 1: "大部晴朗", 2: "多云", 3: "阴天",
    45: "雾", 48: "沉积雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷暴", 96: "雷暴+小冰雹", 99: "雷暴+大冰雹",
}

# 恶劣天气代码（用于安全预警）
SEVERE_WEATHER_CODES = {65, 75, 82, 86, 95, 96, 99}
CAUTION_WEATHER_CODES = {63, 73, 80, 81, 85}


async def fetch_weather(lat: float, lng: float, days: int = 5, start_date: str | None = None) -> dict:
    """
    获取指定坐标的天气预报。

    Args:
        lat: 纬度
        lng: 经度
        days: 预报天数（默认5天）
        start_date: 徒步出发日期（YYYY-MM-DD），指定后从该日期起切取预报

    Returns:
        {
            "latitude": float, "longitude": float,
            "daily": [
                {
                    "date": "2026-08-03",
                    "temp_max_c": 28.5, "temp_min_c": 18.2,
                    "precip_prob": 30,        # 降水概率 %
                    "wind_max_kmh": 25.0,
                    "weather_code": 2,
                    "weather_desc": "多云",
                    "is_severe": false,        # 恶劣天气
                    "is_caution": false,       # 需注意
                },
                ...
            ],
            "summary": "未来5天以多云为主，第3天有中雨，请注意",
            "has_severe": false,
            "has_caution": true,
        }
    """
    # 计算出发日相对今天的偏移（Open-Meteo 仅支持从今天起预报，最多16天）
    offset_days = 0
    if start_date:
        try:
            start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            offset_days = (start - date.today()).days
            if offset_days < 0:
                offset_days = 0  # 已出发，退化为显示最近预报
        except ValueError:
            offset_days = 0

    # 出发日超出免费预报窗口 → 提示无法获取该时段天气
    if offset_days >= 16:
        return {
            "latitude": lat,
            "longitude": lng,
            "daily": [],
            "summary": f"出发日期 {start_date} 超出免费天气预报窗口（最多16天），出发前请重新查询",
            "has_severe": False,
            "has_caution": False,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,"
                        "wind_speed_10m_max,weather_code"
                    ),
                    "timezone": "Asia/Shanghai",
                    "forecast_days": min(offset_days + days, 16),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        daily_raw = data.get("daily", {})
        daily = []

        for i in range(len(daily_raw.get("time", []))):
            code = daily_raw["weather_code"][i]
            daily.append({
                "date": daily_raw["time"][i],
                "temp_max_c": daily_raw["temperature_2m_max"][i],
                "temp_min_c": daily_raw["temperature_2m_min"][i],
                "precip_prob": daily_raw["precipitation_probability_max"][i],
                "wind_max_kmh": daily_raw["wind_speed_10m_max"][i],
                "weather_code": code,
                "weather_desc": WEATHER_CODES.get(code, f"未知({code})"),
                "is_severe": code in SEVERE_WEATHER_CODES,
                "is_caution": code in CAUTION_WEATHER_CODES,
            })

        # 若指定出发日期，切取对应时段（仅保留徒步期间天气）
        if offset_days > 0:
            daily = daily[offset_days:]

        has_severe = any(d["is_severe"] for d in daily)
        has_caution = any(d["is_caution"] for d in daily)

        # 生成摘要
        summary = _generate_summary(daily)

        return {
            "latitude": data.get("latitude", lat),
            "longitude": data.get("longitude", lng),
            "daily": daily,
            "summary": summary,
            "has_severe": has_severe,
            "has_caution": has_caution,
        }

    except Exception as e:
        logger.error(f"[Weather] 获取天气失败 ({lat},{lng}): {e}")
        return {
            "latitude": lat,
            "longitude": lng,
            "daily": [],
            "summary": f"天气数据获取失败: {e}",
            "has_severe": False,
            "has_caution": False,
            "error": str(e),
        }


def _generate_summary(daily: list[dict]) -> str:
    """根据每日天气预报生成中文摘要"""
    if not daily:
        return "暂无天气预报数据"

    parts = []
    for d in daily[:5]:
        date_str = d["date"][5:]  # "MM-DD"
        parts.append(
            f"{date_str} {d['weather_desc']} {d['temp_min_c']:.0f}~{d['temp_max_c']:.0f}°C"
        )

    # 添加警告
    warnings = []
    if any(d["is_severe"] for d in daily):
        warnings.append("⚠️ 有恶劣天气，不建议徒步")
    elif any(d["is_caution"] for d in daily):
        warnings.append("⚠️ 部分日期有降雨/大风，需注意安全")

    if any(d["temp_min_c"] < 0 for d in daily):
        warnings.append("❄️ 低温天气，注意保暖和防滑")

    if any(d["wind_max_kmh"] > 30 for d in daily):
        warnings.append("💨 有大风天气，注意防风")

    base = "未来天气: " + "; ".join(parts[:3]) + ("..." if len(parts) > 3 else "")
    if warnings:
        base += " | " + " | ".join(warnings)

    return base


def get_hiking_weather_advice(weather: dict) -> dict:
    """
    根据天气数据生成徒步建议。

    Returns:
        {
            "go_nogo": "go" | "conditional_go" | "no_go",
            "risk_factors": [...],
            "gear_notes": [...],
            "overall": "综合建议文本",
        }
    """
    daily = weather.get("daily", [])
    if not daily:
        return {
            "go_nogo": "conditional_go",
            "risk_factors": ["无法获取天气数据，请自行评估"],
            "gear_notes": ["建议携带雨具以防万一"],
            "overall": "天气数据不可用，建议查询当地天气预报后决定",
        }

    risk_factors = []
    gear_notes = []
    go_nogo = "go"

    for d in daily:
        date_str = d["date"]

        if d["is_severe"]:
            go_nogo = "no_go"
            risk_factors.append(f"{date_str}: {d['weather_desc']} — 恶劣天气，不宜徒步")

        if d["is_caution"] and go_nogo != "no_go":
            go_nogo = "conditional_go"
            risk_factors.append(f"{date_str}: {d['weather_desc']} — 需注意安全")

        if d["temp_min_c"] < 5:
            gear_notes.append("携带保暖内衣、羽绒服")
        if d["temp_min_c"] < 0:
            gear_notes.append("携带冰爪、雪套，注意防滑")
        if d["temp_max_c"] > 30:
            gear_notes.append("携带充足饮水（建议3L+），防晒霜SPF50+")
        if d["precip_prob"] > 50:
            gear_notes.append("携带防水冲锋衣裤、背包防雨罩")
        if d["wind_max_kmh"] > 30:
            gear_notes.append("携带防风外套，避免在山脊停留")

    # 去重
    gear_notes = list(dict.fromkeys(gear_notes))

    if go_nogo == "no_go":
        overall = "天气条件恶劣，强烈建议推迟行程。如果必须前往，请做好充分安全准备。"
    elif go_nogo == "conditional_go":
        overall = "天气条件一般，可以前往但需做好应对准备。请关注天气变化，必要时及时下撤。"
    else:
        overall = "天气条件良好，适合徒步。请仍按常规做好安全准备。"

    return {
        "go_nogo": go_nogo,
        "risk_factors": risk_factors,
        "gear_notes": gear_notes,
        "overall": overall,
    }
