"""背包方案 API 测试：CRUD / 预设创建 / 装备挂载 / 权限隔离"""
import uuid


async def test_backpack_crud(client, auth_headers):
    headers = auth_headers["headers"]
    # 创建
    r = await client.post("/api/backpacks/", headers=headers, json={
        "name": "周末标准包", "description": "两日露营", "base_weight": 2200,
    })
    assert r.status_code == 200
    bp = r.json()
    assert bp["name"] == "周末标准包"
    assert bp["base_weight"] == 2200
    assert bp["item_count"] == 0
    assert bp["total_weight"] == 2200

    # 列表
    bps = (await client.get("/api/backpacks/", headers=headers)).json()
    assert len(bps) == 1
    assert bps[0]["id"] == bp["id"]

    # 更新
    upd = await client.put(f"/api/backpacks/{bp['id']}", headers=headers, json={
        "name": "周末标准包Pro", "description": "", "base_weight": 2000,
    })
    assert upd.status_code == 200
    assert upd.json()["name"] == "周末标准包Pro"

    # 删除
    d = await client.delete(f"/api/backpacks/{bp['id']}", headers=headers)
    assert d.status_code == 200
    bps2 = (await client.get("/api/backpacks/", headers=headers)).json()
    assert len(bps2) == 0


async def test_backpack_preset_creation(client, auth_headers):
    """预设创建：自动生成装备并挂载，重量计算正确"""
    headers = auth_headers["headers"]
    # 确保分类存在
    await client.post("/api/equipment/init-defaults")

    r = await client.post("/api/backpacks/preset/标准周末", headers=headers)
    assert r.status_code == 200
    bp = r.json()
    assert bp["name"] == "标准周末"
    assert bp["item_count"] >= 8
    assert len(bp["items"]) >= 8
    assert bp["total_weight"] > bp["base_weight"]  # 装备重量已计入

    # 装备确实挂载成功
    items = (await client.get("/api/equipment/items", headers=headers)).json()
    assigned = [i for i in items if i.get("backpack_id") == bp["id"]]
    assert len(assigned) == len(bp["items"])

    # 不存在的预设 → 404
    bad = await client.post("/api/backpacks/preset/不存在方案", headers=headers)
    assert bad.status_code == 404


async def test_backpack_assign_unassign_item(client, auth_headers):
    headers = auth_headers["headers"]
    await client.post("/api/equipment/init-defaults")
    cats = (await client.get("/api/equipment/categories")).json()
    item = (await client.post("/api/equipment/items", headers=headers, json={
        "category_id": cats[0]["id"], "name": "我的帐篷", "brand": "", "model": "",
        "weight": 2000, "quantity": 1, "description": "",
    })).json()
    bp = (await client.post("/api/backpacks/", headers=headers, json={
        "name": "测试包", "description": "", "base_weight": 1000,
    })).json()

    # 挂载
    assigned = await client.post(f"/api/backpacks/{bp['id']}/items/{item['id']}", headers=headers)
    assert assigned.status_code == 200
    assert assigned.json()["item_count"] == 1
    assert assigned.json()["items"][0]["name"] == "我的帐篷"

    # 解绑
    un = await client.delete(f"/api/backpacks/{bp['id']}/items/{item['id']}", headers=headers)
    assert un.status_code == 200
    assert un.json()["item_count"] == 0


async def test_backpack_permission_isolation(client, auth_headers, second_user):
    headers = auth_headers["headers"]
    bp = (await client.post("/api/backpacks/", headers=headers, json={
        "name": "我的包", "description": "", "base_weight": 0,
    })).json()

    # 他人看不到/改不了/删不了
    others = (await client.get("/api/backpacks/", headers=second_user["headers"])).json()
    assert not any(b["id"] == bp["id"] for b in others)
    upd = await client.put(f"/api/backpacks/{bp['id']}", headers=second_user["headers"], json={
        "name": "被改", "description": "", "base_weight": 0,
    })
    assert upd.status_code == 404
    d = await client.delete(f"/api/backpacks/{bp['id']}", headers=second_user["headers"])
    assert d.status_code == 404


async def test_backpack_requires_auth(client):
    assert (await client.get("/api/backpacks/")).status_code == 401
    assert (await client.post("/api/backpacks/", json={"name": "x"})).status_code == 401
