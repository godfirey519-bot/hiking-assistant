"""P3-1 演示账号种子：创建 demo 账号并填充完整数据供真实用户测试。

填充内容:
  1. 真实 AI 工作流生成 1 个完整方案（武功山 2 天 1 夜）
  2. 装备库 53 件（预设模板，含重量）
  3. 背包方案 2 套（标准周末 / 轻装单日）
  4. 徒步记录 1 条

用法: python scripts/seed_demo_data.py
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

API = "http://127.0.0.1:8001"
TSX = Path(r"D:\徒步助手\frontend\src\pages\Equipment.tsx")
DEMO = {"username": "demo", "email": "demo@hiking.app", "password": "demo123456"}


def http(method, path, body=None, token=None, timeout=30):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def extract_templates():
    src = TSX.read_text(encoding="utf-8")
    m = re.search(r"const DEFAULT_ITEMS[^=]*=\s*\{(.*?)\n\}", src, re.S)
    block = m.group(1)
    templates = {}
    for cb in re.split(r"\n\s{2}'", block)[1:]:
        name = cb.split("'")[0]
        items = re.findall(r"\{\s*name:\s*'([^']+)'[^}]*?quantity:\s*(\d+)[^}]*?weight:\s*(\d+)", cb)
        templates[name] = [{"name": n, "quantity": int(q), "weight": int(w)} for n, q, w in items]
    return templates


def main():
    # 1) 注册
    try:
        http("POST", "/api/auth/register", DEMO)
        print("✅ 注册 demo 账号")
    except Exception:
        print("ℹ️ demo 账号已存在")
    login = http("POST", "/api/auth/login", {"username": DEMO["username"], "password": DEMO["password"]})
    token = login["access_token"]
    print("✅ 登录成功")

    # 2) 真实工作流生成方案
    existing = http("GET", "/api/plans/", token=token)
    if not existing:
        plan = http("POST", "/api/plans/", {
            "title": "国庆武功山穿越 2 天 1 夜", "description": "沈子村上金顶，新手，标准预算",
            "participants": 2,
        }, token=token)
        http("POST", f"/api/agents/start-planning/{plan['id']}", {}, token=token)
        print(f"⏳ 等待 AI 工作流完成 (plan #{plan['id']})...")
        for _ in range(60):
            time.sleep(2)
            p = http("GET", f"/api/plans/{plan['id']}", token=token)
            if p["status"] in ("completed", "failed"):
                print(f"✅ 方案生成: {p['status']} | sections={len(p['sections'])}")
                break
        else:
            print("⚠️ 方案生成超时")
    else:
        print(f"ℹ️ 已有 {len(existing)} 个方案，跳过")

    # 3) 装备库填充（预设模板 53 件）
    items = http("GET", "/api/equipment/items", token=token)
    if not items:
        http("POST", "/api/equipment/init-defaults")
        cats = {c["name"]: c["id"] for c in http("GET", "/api/equipment/categories")}
        templates = extract_templates()
        count = 0
        for name, tpl in templates.items():
            cid = cats.get(name)
            if not cid:
                continue
            for it in tpl:
                http("POST", "/api/equipment/items", {
                    "category_id": cid, "name": it["name"], "brand": "", "model": "",
                    "weight": it["weight"], "quantity": it["quantity"], "description": "",
                }, token=token)
                count += 1
        print(f"✅ 装备库填充 {count} 件")
    else:
        print(f"ℹ️ 已有 {len(items)} 件装备，跳过")

    # 4) 背包方案
    bps = http("GET", "/api/backpacks/", token=token)
    if len(bps) < 2:
        from urllib.parse import quote
        for preset in ("标准周末", "轻装单日"):
            try:
                bp = http("POST", f"/api/backpacks/preset/{quote(preset)}", {}, token=token)
                print(f"✅ 背包方案「{bp['name']}」: {len(bp['items'])} 件")
            except Exception as e:
                print(f"⚠️ 背包预设失败: {e}")
    else:
        print(f"ℹ️ 已有 {len(bps)} 个背包方案，跳过")

    # 5) 徒步记录
    trips = http("GET", "/api/trips/", token=token)
    if not trips:
        http("POST", "/api/trips/", {
            "title": "武功山金顶 2 日穿越", "description": "金顶日出绝美，云海壮观",
            "start_date": "2026-08-15", "end_date": "2026-08-16",
            "actual_distance": 22.5, "actual_elevation_gain": 1800,
            "rating": 5, "weather": "晴，山顶有风", "notes": "记得带护膝！",
        }, token=token)
        print("✅ 徒步记录已创建")
    else:
        print(f"ℹ️ 已有 {len(trips)} 条记录，跳过")

    print("\n🎉 demo 账号就绪: username=demo / password=demo123456")
    print("   登录 http://localhost:5173 即可开始真实用户测试")


if __name__ == "__main__":
    main()
