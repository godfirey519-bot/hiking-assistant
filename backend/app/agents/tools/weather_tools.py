"""天气查询工具 — Agent 用于获取天气预报"""
import logging

logger = logging.getLogger(__name__)


async def check_weather(location: str, date: str | None = None) -> dict:
    """
    查询指定地点和日期的天气。

    在实际部署中替换为真实的 OpenWeatherMap/和风天气 API。

    Args:
        location: 地点名称或坐标
        date: 日期 (YYYY-MM-DD)，None 为当前

    Returns:
        天气数据
    """
    logger.info(f"[Weather] 查询 {location} 的天气 (date={date})")

    # TODO: 集成真实天气 API
    # API示例: https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={key}

    return {
        "location": location,
        "date": date or "今天",
        "temperature_high_c": 20,
        "temperature_low_c": 8,
        "condition": "晴间多云",
        "precipitation_probability": 20,
        "wind_speed_kmh": 15,
        "wind_gust_kmh": 25,
        "humidity_percent": 65,
        "uv_index": 6,
        "visibility_km": 10,
        "sunrise": "06:15",
        "sunset": "18:30",
        "warning": None,  # 天气预警
        "note": "（实际部署时将返回真实天气数据）",
    }


# 徒步天气风险评估
def assess_weather_risk(weather: dict) -> dict:
    """根据天气数据评估徒步风险"""
    risks = []
    risk_level = 0

    if weather.get("precipitation_probability", 0) > 60:
        risks.append("高降雨概率，需携带雨具和防水装备")
        risk_level += 2

    if weather.get("wind_speed_kmh", 0) > 30:
        risks.append("强风天气，注意山口和山脊区域")
        risk_level += 2

    if weather.get("wind_gust_kmh", 0) > 50:
        risks.append("阵风强度危险，不建议在山脊行走")
        risk_level += 3

    temp_high = weather.get("temperature_high_c", 20)
    temp_low = weather.get("temperature_low_c", 10)
    temp_range = temp_high - temp_low

    if temp_range > 20:
        risks.append(f"昼夜温差大 ({temp_range}°C)，需准备保暖层和防晒")
        risk_level += 1

    if temp_low < 0:
        risks.append("夜间低于零度，需准备保暖睡袋和防寒装备")
        risk_level += 2

    if weather.get("uv_index", 0) > 8:
        risks.append("紫外线强度高，需准备防晒装备")
        risk_level += 1

    if weather.get("visibility_km", 10) < 2:
        risks.append("能见度低，注意导航安全")
        risk_level += 2

    thresholds = [
        (0, "低风险", "天气状况良好，适宜徒步"),
        (3, "中等风险", "需注意天气变化，做好相应准备"),
        (6, "高风险", "天气条件较差，建议谨慎出行或调整计划"),
        (10, "极高风险", "天气条件恶劣，强烈建议取消或推迟徒步"),
    ]

    for threshold, level, advice in thresholds:
        if risk_level <= threshold:
            return {
                "risk_level": level,
                "risk_score": risk_level,
                "risks": risks,
                "advice": advice,
            }

    return {"risk_level": "极高风险", "risk_score": risk_level, "risks": risks, "advice": thresholds[-1][2]}
