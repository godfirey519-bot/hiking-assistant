"""Agent 规则引擎测试（不调用 LLM）：
RouteAnalyst 知识库匹配 / GPX 分析 / EquipmentReviewer / SafetyAssessor
"""
from app.agents.equipment_reviewer import EquipmentReviewerAgent
from app.agents.route_analyst import RouteAnalystAgent
from app.agents.safety_assessor import SafetyAssessorAgent
from app.agents.tools.gpx_tools import analyze_gpx
from app.agents.tools.weather_tools import assess_weather_risk


# ===== RouteAnalyst 知识库匹配 =====

async def test_route_kb_exact_match():
    agent = RouteAnalystAgent()
    result = await agent._analyze_known_route("国庆想去武功山徒步两天")
    assert result.success
    assert result.output["name"] == "武功山"
    assert result.output["distance_km"] > 0
    assert "知识库匹配" in result.thinking


async def test_route_kb_prefix_match():
    """前缀匹配: '格聂' → 格聂C线/格聂V线"""
    agent = RouteAnalystAgent()
    result = await agent._analyze_known_route("格聂环线怎么样")
    assert result.success
    assert result.output["name"].startswith("格聂")


async def test_route_kb_no_match():
    agent = RouteAnalystAgent()
    result = await agent._analyze_known_route("去火星环形山徒步")
    assert result.success
    assert "message" in result.output


async def test_route_kb_query_normalization():
    """规范化匹配：去前缀/后缀，让口语化查询命中知识库"""
    agent = RouteAnalystAgent()
    cases = {
        "想去罗布泊穿越": "罗布泊徒步",
        "想去喀拉峻徒步": "喀拉峻徒步",
        "虎跳峡两天怎么走": "虎跳峡",
        "雨崩攻略": "雨崩",
    }
    for query, expect in cases.items():
        result = await agent._analyze_known_route(query)
        assert result.success, f"{query} 应命中"
        assert result.output.get("name") == expect, f"{query} -> {result.output.get('name')}, 期望 {expect}"


async def test_route_kb_unknown_still_unmatched():
    agent = RouteAnalystAgent()
    result = await agent._analyze_known_route("去一个不存在的地方徒步")
    assert "message" in result.output


async def test_route_think_uses_kb_without_llm():
    """think() 走知识库短路，不触发 LLM，秒回"""
    agent = RouteAnalystAgent()
    result = await agent.think("我想去虎跳峡徒步")
    assert result.success
    assert result.output["name"] == "虎跳峡"
    assert result.output["distance_km"] > 0


async def test_route_gpx_analysis():
    """GPX 数据分析：难度评级/预估时间/分段"""
    waypoints = []
    for i in range(21):
        waypoints.append({"lat": 30.0 + i * 0.001, "lng": 100.0, "ele": 1000 + i * 50})
    gpx = {"distance": 25000, "elevation_gain": 1800, "max_elevation": 3200,
           "min_elevation": 1000, "waypoints": waypoints}
    result = await analyze_gpx(gpx)
    assert result["distance_km"] == 25.0
    assert result["difficulty_score"] >= 3  # 距离+爬升+海拔
    assert result["estimated_days"] >= 1
    assert result["total_segments"] > 0


async def test_route_gpx_easy():
    gpx = {"distance": 3000, "elevation_gain": 200, "max_elevation": 800,
           "min_elevation": 500, "waypoints": []}
    result = await analyze_gpx(gpx)
    assert result["difficulty_level"] in ("轻松", "较易")


# ===== EquipmentReviewer 规则 =====

async def test_equipment_reviewer_missing_safety_gear():
    agent = EquipmentReviewerAgent()
    result = await agent._execute_with_tools("测试", {"equipment_data": {}, "route_data": {}})
    assert result["result"] in ("approved", "needs_modification")
    high_issues = [i for i in result["issues"] if i["severity"] == "high"]
    assert len(high_issues) >= 3  # 缺少 急救/照明/导航 等关键类别
    assert result["score"] <= 60
    assert result["weight_analysis"]["estimated_total_kg"] == 12.0  # 无数据默认 12kg


async def test_equipment_reviewer_complete():
    agent = EquipmentReviewerAgent()
    equipment = {
        "equipment_by_category": {
            "睡眠系统": [{"name": "帐篷", "category": "睡眠系统"}],
            "照明": [{"name": "头灯", "category": "照明"}],
            "急救": [{"name": "急救包", "category": "急救"}],
            "导航通讯": [{"name": "手机", "category": "导航通讯"}],
            "饮水": [{"name": "水袋", "category": "饮水"}],
        }
    }
    result = await agent._execute_with_tools("测试", {"equipment_data": equipment, "route_data": {}})
    assert result["score"] == 100
    assert result["result"] == "approved"


async def test_equipment_reviewer_high_altitude_needs_down_jacket():
    agent = EquipmentReviewerAgent()
    equipment = {
        "equipment_by_category": {
            "睡眠系统": [{"name": "帐篷", "category": "睡眠系统"}],
            "照明": [{"name": "头灯", "category": "照明"}],
            "急救": [{"name": "急救包", "category": "急救"}],
            "导航通讯": [{"name": "手机", "category": "导航通讯"}],
            "饮水": [{"name": "水袋", "category": "饮水"}],
        }
    }
    result = await agent._execute_with_tools("测试", {
        "equipment_data": equipment, "route_data": {"max_elevation_m": 4500},
    })
    assert any("羽绒服" in i["problem"] for i in result["issues"])


# ===== SafetyAssessor 规则 =====

async def test_safety_high_altitude_hard_route():
    agent = SafetyAssessorAgent()
    result = await agent._execute_with_tools("测试", {
        "route_data": {"difficulty": "困难", "max_elevation_m": 4500},
        "equipment_review": {},
    })
    assert any(r["category"] == "高海拔" for r in result["risks"])
    assert result["risk_score"] >= 13  # 困难(8) + 高海拔(5)


async def test_safety_rejected_equipment_raises_risk():
    agent = SafetyAssessorAgent()
    result = await agent._execute_with_tools("测试", {
        "route_data": {"difficulty": "轻松", "max_elevation_m": 500},
        "equipment_review": {"result": "rejected", "score": 30},
    })
    assert result["risk_score"] >= 10
    assert result["go_nogo"] in ("go", "conditional_go", "no_go")


# ===== Weather tools =====

def test_weather_risk_scoring():
    low = assess_weather_risk({"precipitation_probability": 20, "wind_speed_kmh": 10,
                               "wind_gust_kmh": 20, "temperature_high_c": 20,
                               "temperature_low_c": 10, "uv_index": 5, "visibility_km": 10})
    assert low["risk_score"] == 0
    assert low["risk_level"] == "低风险"

    high = assess_weather_risk({"precipitation_probability": 90, "wind_speed_kmh": 40,
                                "wind_gust_kmh": 60, "temperature_high_c": 25,
                                "temperature_low_c": -2, "uv_index": 9, "visibility_km": 1})
    assert high["risk_score"] >= 6
    assert high["risk_level"] in ("高风险", "极高风险")
