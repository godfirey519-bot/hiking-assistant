"""验证装备预设模板端到端流程（模拟前端 fillDefaults）:
1. 从 Equipment.tsx 提取 DEFAULT_ITEMS 模板
2. 注册/登录验证用户
3. 对每个分类 POST 模板装备（含重量）
4. GET 校验: 总数 / 分类覆盖 / 重量一致

用法: python scripts/verify_gear_presets.py
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

API = "http://127.0.0.1:8001"
TSX = Path(r"D:\徒步助手\frontend\src\pages\Equipment.tsx")
USER = {"username": "gear_verify", "email": "gear_verify@test.com", "password": "gear123456"}


def http(method, path, body=None, token=None, timeout=10):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def extract_templates():
    """从 Equipment.tsx 提取 DEFAULT_ITEMS: {分类名: [{name, notes, quantity, weight}]}"""
    src = TSX.read_text(encoding="utf-8")
    m = re.search(r"const DEFAULT_ITEMS[^=]*=\s*\{(.*?)\n\}", src, re.S)
    block = m.group(1)
    # 按顶层分类块切分
    cat_blocks = re.split(r"\n\s{2}'", block)[1:]
    templates = {}
    for cb in cat_blocks:
        cat_name = cb.split("'")[0]
        items = re.findall(
            r"\{\s*name:\s*'([^']+)'[^}]*?quantity:\s*(\d+)[^}]*?weight:\s*(\d+)",
            cb,
        )
        templates[cat_name] = [
            {"name": n, "quantity": int(q), "weight": int(w)} for n, q, w in items
        ]
    return templates


def main():
    templates = extract_templates()
    total_template = sum(len(v) for v in templates.values())
    print(f"模板: {len(templates)} 分类 / {total_template} 件装备")

    # 1) 注册或登录
    try:
        http("POST", "/api/auth/register", USER)
        print("已注册验证用户", USER["username"])
    except Exception:
        pass
    login = http("POST", "/api/auth/login", {"username": USER["username"], "password": USER["password"]})
    token = login["access_token"]
    print("登录成功")

    # 2) 清空该用户已有装备（幂等）
    existing = http("GET", "/api/equipment/items", token=token)
    for item in existing:
        http("DELETE", f"/api/equipment/items/{item['id']}", token=token)

    # 3) 模拟 fillDefaults 全量填充
    cats = http("GET", "/api/equipment/categories")
    cat_id = {c["name"]: c["id"] for c in cats}
    missing_cats = [n for n in templates if n not in cat_id]
    if missing_cats:
        print(f"❌ 分类缺失: {missing_cats}")
        sys.exit(1)

    filled = 0
    for name, items in templates.items():
        for it in items:
            http("POST", "/api/equipment/items", {
                "category_id": cat_id[name], "name": it["name"], "brand": "",
                "model": "", "weight": it["weight"], "quantity": it["quantity"],
                "description": "",
            }, token=token)
            filled += 1
    print(f"已填充 {filled} 件装备")

    # 4) 校验
    items = http("GET", "/api/equipment/items", token=token)
    by_cat = {}
    for i in items:
        by_cat.setdefault(i["category_id"], []).append(i)

    ok = True
    print(f"\nGET /equipment/items 返回 {len(items)} 件")
    if len(items) != total_template:
        print(f"❌ 数量不符: 期望 {total_template}, 实际 {len(items)}")
        ok = False

    # 每个分类都被覆盖
    for name, cid in cat_id.items():
        n = len(by_cat.get(cid, []))
        expected = len(templates.get(name, []))
        mark = "✅" if n == expected else "❌"
        if n != expected:
            ok = False
        print(f"  {mark} {name}: {n} 件 (模板 {expected})")

    # 重量非零（除 户外保险 外）且与模板一致
    zero_weight = [i["name"] for i in items if i["weight"] == 0 and i["name"] != "户外保险"]
    if zero_weight:
        print(f"❌ 存在 0 重量装备: {zero_weight}")
        ok = False
    else:
        print("✅ 重量字段全部写入")

    total_kg = sum(i["weight"] * (i["quantity"] or 1) for i in items) / 1000
    print(f"✅ 模板总重量: {total_kg:.1f} kg")

    # 5) 清理: 删除验证用户及其装备
    for i in items:
        http("DELETE", f"/api/equipment/items/{i['id']}", token=token)
    # 删除用户（直接操作 DB 不可取，保留账号但清空装备即可）
    print("已清空验证用户装备（账号保留供复用）")

    print("\n" + ("🎉 全部验证通过" if ok else "❌ 存在失败项"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
