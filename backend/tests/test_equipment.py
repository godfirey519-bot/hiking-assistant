"""装备模块测试：分类初始化/装备 CRUD/权限隔离"""
import uuid


async def test_init_defaults_creates_13_categories(client):
    r = await client.post("/api/equipment/init-defaults")
    assert r.status_code == 200
    cats = (await client.get("/api/equipment/categories")).json()
    assert len(cats) == 13
    # 幂等：再次调用不重复创建
    await client.post("/api/equipment/init-defaults")
    cats2 = (await client.get("/api/equipment/categories")).json()
    assert len(cats2) == 13


async def test_gear_crud(client, auth_headers):
    headers = auth_headers["headers"]
    cats = (await client.get("/api/equipment/categories")).json()
    target_cat = next(c for c in cats if c["name"] == "睡眠系统")

    # 创建
    r = await client.post("/api/equipment/items", headers=headers, json={
        "category_id": target_cat["id"], "name": "测试帐篷", "brand": "三峰出",
        "model": "", "weight": 2000, "quantity": 1, "description": "三季帐",
    })
    assert r.status_code == 200
    item = r.json()
    assert item["weight"] == 2000
    assert item["category"]["name"] == "睡眠系统"

    # 列表
    items = (await client.get("/api/equipment/items", headers=headers)).json()
    assert any(i["id"] == item["id"] for i in items)

    # 更新
    upd = await client.put(f"/api/equipment/items/{item['id']}", headers=headers, json={
        "category_id": target_cat["id"], "name": "测试帐篷 Pro", "brand": "MSR",
        "model": "", "weight": 1800, "quantity": 2, "description": "",
    })
    assert upd.status_code == 200
    assert upd.json()["weight"] == 1800

    # 删除
    d = await client.delete(f"/api/equipment/items/{item['id']}", headers=headers)
    assert d.status_code == 200
    items2 = (await client.get("/api/equipment/items", headers=headers)).json()
    assert not any(i["id"] == item["id"] for i in items2)


async def test_gear_permission_isolation(client, auth_headers, second_user):
    """A 用户创建的装备对 B 用户不可见/不可改"""
    cats = (await client.get("/api/equipment/categories")).json()
    target_cat = cats[0]

    r = await client.post("/api/equipment/items", headers=auth_headers["headers"], json={
        "category_id": target_cat["id"], "name": "我的帐篷", "brand": "", "model": "",
        "weight": 1000, "quantity": 1, "description": "",
    })
    item_id = r.json()["id"]

    # B 看不到
    b_items = (await client.get("/api/equipment/items", headers=second_user["headers"])).json()
    assert not any(i["id"] == item_id for i in b_items)

    # B 改不了/删不了
    upd = await client.put(f"/api/equipment/items/{item_id}", headers=second_user["headers"], json={
        "category_id": target_cat["id"], "name": "被改", "brand": "", "model": "",
        "weight": 1, "quantity": 1, "description": "",
    })
    assert upd.status_code == 404
    d = await client.delete(f"/api/equipment/items/{item_id}", headers=second_user["headers"])
    assert d.status_code == 404


async def test_gear_requires_auth(client):
    r = await client.get("/api/equipment/items")
    assert r.status_code == 401


async def test_gear_update_delete_not_found(client, auth_headers):
    """更新/删除不存在的装备 → 404"""
    headers = auth_headers["headers"]
    upd = await client.put("/api/equipment/items/99999", headers=headers, json={
        "category_id": 1, "name": "x", "brand": "", "model": "",
        "weight": 1, "quantity": 1, "description": "",
    })
    assert upd.status_code == 404
    d = await client.delete("/api/equipment/items/99999", headers=headers)
    assert d.status_code == 404


async def test_gear_create_with_invalid_category(client, auth_headers):
    """不存在的分类 → 400（已修复：此前会 500 IntegrityError）"""
    r = await client.post("/api/equipment/items", headers=auth_headers["headers"], json={
        "category_id": 99999, "name": "x", "brand": "", "model": "",
        "weight": 1, "quantity": 1, "description": "",
    })
    assert r.status_code == 400


async def test_gear_list_filter_by_category(client, auth_headers):
    headers = auth_headers["headers"]
    cats = (await client.get("/api/equipment/categories")).json()
    c1, c2 = cats[0], cats[1]
    await client.post("/api/equipment/items", headers=headers, json={
        "category_id": c1["id"], "name": "甲类装备", "brand": "", "model": "",
        "weight": 100, "quantity": 1, "description": "",
    })
    await client.post("/api/equipment/items", headers=headers, json={
        "category_id": c2["id"], "name": "乙类装备", "brand": "", "model": "",
        "weight": 200, "quantity": 1, "description": "",
    })
    only_c1 = (await client.get(f"/api/equipment/items?category_id={c1['id']}", headers=headers)).json()
    assert len(only_c1) == 1
    assert only_c1[0]["name"] == "甲类装备"


async def test_create_category_requires_auth(client):
    r = await client.post("/api/equipment/categories", json={"name": "测试分类", "icon": "package", "sort_order": 50})
    assert r.status_code == 401
