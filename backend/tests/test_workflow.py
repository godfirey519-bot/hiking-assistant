"""规划工作流集成测试：execute_planning 全链路（mock LLM 降级 + 天气 API）"""
import pytest

from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services.plan_service import execute_planning


async def _create_plan(client, headers):
    r = await client.post("/api/plans/", headers=headers, json={
        "title": "周末去武功山两天一夜",
        "description": "新手，有基础装备，想轻松一点",
        "participants": 2,
    })
    assert r.status_code == 200
    return r.json()


async def test_execute_planning_full_workflow(client, auth_headers, monkeypatch):
    """完整工作流：知识库路线(武功山) + mock天气 + LLM降级规则 → completed 方案"""
    plan = await _create_plan(client, auth_headers["headers"])

    # 1) mock LLM 不可用 → 所有 Agent 走规则降级（不触网）
    class FakeLLM:
        available = False

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FakeLLM())

    # 2) mock 天气 API（避免真实网络）
    async def fake_fetch(lat, lng, days, start_date=None):
        return {
            "latitude": lat, "longitude": lng,
            "daily": [{
                "date": "2026-09-01", "temp_max_c": 22.0, "temp_min_c": 12.0,
                "precip_prob": 20, "wind_max_kmh": 15.0, "weather_code": 1,
                "weather_desc": "晴", "is_severe": False, "is_caution": False,
            }],
            "summary": "测试天气：晴", "has_severe": False, "has_caution": False,
        }

    monkeypatch.setattr("app.services.weather_service.fetch_weather", fake_fetch)

    async with async_session() as db:
        user = (await db.execute(select(User).where(User.id == auth_headers["user_id"]))).scalar_one()
        result = await execute_planning(plan["id"], user, db)

    assert result["success"] is True
    assert result["route_data"]["name"] == "武功山"
    assert result["equipment_data"]["total_items"] > 0
    assert result["meal_data"]["daily"]

    # 3) 校验落库结果
    got = (await client.get(f"/api/plans/{plan['id']}", headers=auth_headers["headers"])).json()
    assert got["status"] == "completed"
    types = {s["type"] for s in got["sections"]}
    assert {"route", "equipment", "safety", "meal", "weather", "schedule", "summary"} <= types
    assert len(got["agent_logs"]) >= 6  # RouteAnalyst/Weather/Equipment/Reviewer/Safety/Meal/Synth
    agents = {log["agent_name"] for log in got["agent_logs"]}
    assert "Synthesizer" in agents and "SafetyAssessor" in agents


async def test_execute_planning_unknown_route(client, auth_headers, monkeypatch):
    """未知路线 + LLM 不可用 → 工作流仍完成（规则兜底）"""
    r = await client.post("/api/plans/", headers=auth_headers["headers"], json={
        "title": "去一个不存在的秘密山谷徒步",
        "description": "三天两夜",
    })
    plan = r.json()

    class FakeLLM:
        available = False
    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FakeLLM())

    async def fake_fetch(lat, lng, days, start_date=None):
        return {"daily": [], "summary": "无数据", "has_severe": False, "has_caution": False}
    monkeypatch.setattr("app.services.weather_service.fetch_weather", fake_fetch)

    async with async_session() as db:
        user = (await db.execute(select(User).where(User.id == auth_headers["user_id"]))).scalar_one()
        result = await execute_planning(plan["id"], user, db)

    # 未知路线知识库未命中 → 规则兜底仍能完成（plan 状态 completed）
    assert result["success"] is True
    got = (await client.get(f"/api/plans/{plan['id']}", headers=auth_headers["headers"])).json()
    assert got["status"] == "completed"
