"""规划模块测试：方案 CRUD + 权限隔离 + Agent 工作流状态机（mock 掉 LLM 执行）"""
import asyncio
import uuid


async def _create_plan(client, headers, title="测试方案"):
    r = await client.post("/api/plans/", headers=headers, json={
        "title": title,
        "description": "周末去武功山，两天一夜，新手",
        "participants": 2,
    })
    assert r.status_code == 200
    return r.json()


async def test_create_and_get_plan(client, auth_headers):
    headers = auth_headers["headers"]
    plan = await _create_plan(client, headers)
    assert plan["status"] == "draft"
    assert plan["title"] == "测试方案"

    got = await client.get(f"/api/plans/{plan['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["sections"] == []
    assert got.json()["agent_logs"] == []


async def test_list_plans(client, auth_headers):
    headers = auth_headers["headers"]
    await _create_plan(client, headers, "方案A")
    await _create_plan(client, headers, "方案B")
    plans = (await client.get("/api/plans/", headers=headers)).json()
    assert len(plans) == 2
    assert {p["title"] for p in plans} == {"方案A", "方案B"}


async def test_plan_permission_isolation(client, auth_headers, second_user):
    plan = await _create_plan(client, auth_headers["headers"])
    # 他人看不到/删不了
    got = await client.get(f"/api/plans/{plan['id']}", headers=second_user["headers"])
    assert got.status_code == 404
    d = await client.delete(f"/api/plans/{plan['id']}", headers=second_user["headers"])
    assert d.status_code == 404
    # 本人可删
    d2 = await client.delete(f"/api/plans/{plan['id']}", headers=auth_headers["headers"])
    assert d2.status_code == 200


async def test_plan_requires_auth(client):
    assert (await client.get("/api/plans/")).status_code == 401
    assert (await client.post("/api/plans/", json={"title": "x"})).status_code == 401


async def test_start_planning_workflow(client, auth_headers, monkeypatch):
    """触发 Agent 工作流：状态 draft → planning → completed（mock 执行）"""
    plan = await _create_plan(client, auth_headers["headers"])
    headers = auth_headers["headers"]

    async def fake_execute_planning(plan_id, user, db):
        # 模拟完整工作流：写入一条 Synthesizer 完成日志并置状态 completed
        from app.models.plan import Plan, PlanAgentLog
        from sqlalchemy import select
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        p = result.scalar_one()
        p.status = "completed"
        db.add(PlanAgentLog(plan_id=plan_id, agent_name="Synthesizer",
                            role="synthesizer", status="completed",
                            input="{}", output="{}", thinking="mock"))
        await db.commit()

    monkeypatch.setattr("app.services.plan_service.execute_planning", fake_execute_planning)

    r = await client.post(f"/api/agents/start-planning/{plan['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    # 立即查询应为 planning
    p1 = (await client.get(f"/api/plans/{plan['id']}", headers=headers)).json()
    assert p1["status"] in ("planning", "completed")

    # 等待后台任务完成
    for _ in range(20):
        await asyncio.sleep(0.1)
        p2 = (await client.get(f"/api/plans/{plan['id']}", headers=headers)).json()
        if p2["status"] == "completed":
            break

    assert p2["status"] == "completed"
    assert any(log["agent_name"] == "Synthesizer" and log["status"] == "completed" for log in p2["agent_logs"])


async def test_start_planning_other_users_plan_404(client, auth_headers, second_user):
    plan = await _create_plan(client, auth_headers["headers"])
    r = await client.post(f"/api/agents/start-planning/{plan['id']}", headers=second_user["headers"])
    assert r.status_code == 404
