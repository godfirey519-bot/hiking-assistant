"""徒步记录 API 测试：创建/列表/详情/删除/权限隔离（含 media 懒加载回归）"""
import uuid


async def _create_trip(client, headers, title="测试徒步"):
    r = await client.post("/api/trips/", headers=headers, json={
        "title": title,
        "description": "周末徒步",
        "start_date": "2026-09-01",
        "end_date": "2026-09-02",
        "actual_distance": 22.5,
        "actual_elevation_gain": 1800,
        "rating": 4,
        "weather": "晴",
        "notes": "风景不错",
    })
    assert r.status_code == 200
    return r.json()


async def test_trip_crud_and_list_with_media(client, auth_headers):
    """创建 → 列表（含 media 懒加载回归）→ 详情 → 删除"""
    headers = auth_headers["headers"]
    trip = await _create_trip(client, headers)

    # 列表不能 500（此前 media 懒加载导致 MissingGreenlet 崩溃后端）
    trips = (await client.get("/api/trips/", headers=headers)).json()
    assert any(t["id"] == trip["id"] for t in trips)
    listed = next(t for t in trips if t["id"] == trip["id"])
    assert listed["media"] == []
    assert listed["actual_distance"] == 22.5

    # 详情
    got = (await client.get(f"/api/trips/{trip['id']}", headers=headers)).json()
    assert got["title"] == "测试徒步"
    assert got["rating"] == 4

    # 删除
    d = await client.delete(f"/api/trips/{trip['id']}", headers=headers)
    assert d.status_code == 200
    trips2 = (await client.get("/api/trips/", headers=headers)).json()
    assert not any(t["id"] == trip["id"] for t in trips2)


async def test_trip_permission_isolation(client, auth_headers, second_user):
    trip = await _create_trip(client, auth_headers["headers"])
    got = await client.get(f"/api/trips/{trip['id']}", headers=second_user["headers"])
    assert got.status_code == 404
    d = await client.delete(f"/api/trips/{trip['id']}", headers=second_user["headers"])
    assert d.status_code == 404


async def test_trip_requires_auth(client):
    assert (await client.get("/api/trips/")).status_code == 401
    assert (await client.post("/api/trips/", json={"title": "x"})).status_code == 401
