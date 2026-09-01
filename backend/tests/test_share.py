"""分享 API 测试：生成/免登录读取/权限/撤销"""
import uuid


async def _create_completed_plan(client, headers):
    """创建方案并置为 completed（模拟工作流完成）"""
    r = await client.post("/api/plans/", headers=headers, json={
        "title": "分享测试方案", "description": "武功山两天",
    })
    plan = r.json()
    from app.database import async_session
    from app.models.plan import Plan, PlanSection
    from sqlalchemy import select
    async with async_session() as db:
        p = (await db.execute(select(Plan).where(Plan.id == plan["id"]))).scalar_one()
        p.status = "completed"
        db.add(PlanSection(plan_id=p.id, type="route", title="路线分析",
                           content='{"name": "武功山", "distance_km": 30}', agent_name="RouteAnalyst"))
        await db.commit()
    return plan


async def test_share_create_and_read_without_auth(client, auth_headers):
    headers = auth_headers["headers"]
    plan = await _create_completed_plan(client, headers)

    # 生成分享
    r = await client.post(f"/api/share/plans/{plan['id']}", headers=headers)
    assert r.status_code == 200
    share = r.json()
    assert share["token"]
    assert share["url"].startswith("/share/plans/")

    # 幂等：再次生成返回同一 token
    r2 = await client.post(f"/api/share/plans/{plan['id']}", headers=headers)
    assert r2.json()["token"] == share["token"]

    # 免登录读取（无 Authorization）
    got = await client.get(f"/api/share/plans/{share['token']}")
    assert got.status_code == 200
    data = got.json()
    assert data["plan"]["title"] == "分享测试方案"
    assert any(s["type"] == "route" for s in data["plan"]["sections"])

    # 不存在的 token → 404
    bad = await client.get("/api/share/plans/no-such-token-xyz")
    assert bad.status_code == 404


async def test_share_permission(client, auth_headers, second_user):
    """只能分享自己的方案；只能由所有者撤销"""
    plan = await _create_completed_plan(client, auth_headers["headers"])

    # 他人不能为我的方案生成分享
    denied = await client.post(f"/api/share/plans/{plan['id']}", headers=second_user["headers"])
    assert denied.status_code == 404

    # 我生成
    share = (await client.post(f"/api/share/plans/{plan['id']}", headers=auth_headers["headers"])).json()

    # 他人不能撤销
    revoke = await client.delete(f"/api/share/plans/{share['token']}", headers=second_user["headers"])
    assert revoke.status_code in (403, 404)

    # 我可以撤销 → 之后免登录读取 404
    ok = await client.delete(f"/api/share/plans/{share['token']}", headers=auth_headers["headers"])
    assert ok.status_code == 200
    gone = await client.get(f"/api/share/plans/{share['token']}")
    assert gone.status_code == 404


async def test_share_requires_auth_for_create(client):
    assert (await client.post("/api/share/plans/1")).status_code == 401
