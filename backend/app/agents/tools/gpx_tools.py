"""GPX 分析工具 — Agent 用于分析路线数据"""
import logging
import math

logger = logging.getLogger(__name__)


async def analyze_gpx(gpx_data: dict) -> dict:
    """
    分析 GPX 路线数据，提取关键指标供 Agent 使用。

    Args:
        gpx_data: 包含 waypoints, distance, elevation_gain 等字段的路线数据

    Returns:
        路线分析报告
    """
    distance = gpx_data.get("distance", 0)
    elevation_gain = gpx_data.get("elevation_gain", 0)
    max_ele = gpx_data.get("max_elevation", 0)
    min_ele = gpx_data.get("min_elevation", 0)
    waypoints = gpx_data.get("waypoints", [])

    # 难度评级
    difficulty_score = 0
    if distance > 20000:
        difficulty_score += 3
    elif distance > 10000:
        difficulty_score += 2
    elif distance > 5000:
        difficulty_score += 1

    if elevation_gain > 2000:
        difficulty_score += 3
    elif elevation_gain > 1000:
        difficulty_score += 2
    elif elevation_gain > 500:
        difficulty_score += 1

    if max_ele > 4000:
        difficulty_score += 2  # 高海拔
    elif max_ele > 2500:
        difficulty_score += 1

    levels = ["轻松", "较易", "中等", "较难", "困难", "专业级", "极限"]
    difficulty_level = levels[min(difficulty_score, len(levels) - 1)]

    # 预估时间（使用 Naismith 规则: 5km/h + 每600m爬升加1小时）
    base_hours = distance / 5000
    climb_hours = elevation_gain / 600
    estimated_hours = base_hours + climb_hours

    # 分段分析
    segments = _analyze_segments(waypoints)

    return {
        "distance_km": round(distance / 1000, 2),
        "elevation_gain_m": round(elevation_gain),
        "max_elevation_m": round(max_ele),
        "min_elevation_m": round(min_ele),
        "elevation_range_m": round(max_ele - min_ele),
        "difficulty_level": difficulty_level,
        "difficulty_score": difficulty_score,
        "estimated_hours": round(estimated_hours, 1),
        "estimated_days": max(1, math.ceil(estimated_hours / 8)),
        "segments": segments,
        "has_steep_sections": any(s.get("gradient", 0) > 25 for s in segments),
        "total_segments": len(segments),
    }


def _analyze_segments(waypoints: list) -> list[dict]:
    """将路线分段分析"""
    if len(waypoints) < 2:
        return []

    segments = []
    segment_size = max(1, len(waypoints) // 10)  # 约10段

    for i in range(0, len(waypoints) - segment_size, segment_size):
        start = waypoints[i]
        end = waypoints[min(i + segment_size, len(waypoints) - 1)]

        lat1, lat2 = math.radians(start["lat"]), math.radians(end["lat"])
        dlat = lat2 - lat1
        dlon = math.radians(end["lng"] - start["lng"])
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        dist = 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        ele_change = (end.get("ele", 0) or 0) - (start.get("ele", 0) or 0)
        gradient = (ele_change / dist * 100) if dist > 0 else 0

        segments.append({
            "from_km": round(i * 100 / 1000, 2),
            "to_km": round(min(i + segment_size, len(waypoints) - 1) * 100 / 1000, 2),
            "distance_m": round(dist),
            "elevation_change_m": round(ele_change),
            "gradient_percent": round(gradient, 1),
            "type": "上坡" if gradient > 5 else ("下坡" if gradient < -5 else "平路"),
        })

    return segments
