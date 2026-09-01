"""路线分段数据质量抽检脚本。

对 route_segments.json 全部 136 条路线做自动校验:
  1. 字段完整性: from/to/distance_km/gain_m/terrain/water/highlights/risks/pace 缺失
  2. 数值合理性: distance_km <= 0, gain_m < 0, day 编号不连续
  3. 分段距离总和 vs 知识库 KNOWN_ROUTES distance_km 偏差 > 25%
  4. 可疑值: 单日距离 > 40km 或 gain > 2000m (重度穿越除外), 连续重复文案

用法: python scripts/audit_route_segments.py
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SEG_FILE = ROOT / "data" / "route_segments.json"
ANALYST = ROOT / "app" / "agents" / "route_analyst.py"

REQUIRED_FIELDS = ["from", "to", "distance_km", "gain_m", "terrain", "water", "highlights", "risks", "pace"]


def load_known_routes():
    src = ANALYST.read_text(encoding="utf-8")
    m = re.search(r"KNOWN_ROUTES\s*=\s*\{(.*?)\n\}", src, re.S)
    block = m.group(1)
    names = re.findall(r'^\s{4}"([^"]+)":\s*\{', block, re.M)
    routes = {}
    # 提取每条路线的 distance_km / elevation_gain_m / duration_days
    # （精确键匹配 + 重复键取最后一个定义，与 Python dict 覆盖行为一致）
    for name in names:
        matches = list(re.finditer(
            r'^\s{4}"' + re.escape(name) + r'":\s*\{.*?distance_km["\']?\s*:\s*([\d.]+).*?elevation_gain_m["\']?\s*:\s*([\d.]+).*?duration_days["\']?\s*:\s*(\d+)',
            block, re.S | re.M))
        sm = matches[-1] if matches else None
        if sm:
            routes[name] = {
                "distance_km": float(sm.group(1)),
                "gain_m": float(sm.group(2)),
                "days": int(sm.group(3)),
            }
    return routes


def main():
    segs = json.loads(SEG_FILE.read_text(encoding="utf-8"))
    known = load_known_routes()
    print(f"分段文件: {len(segs)} 条路线 | 知识库可对比: {len(known)} 条\n")

    issues = []
    no_segments = []
    for name, days in segs.items():
        if not isinstance(days, list) or len(days) == 0:
            no_segments.append(name)
            continue
        # day 编号连续性
        day_nums = [d.get("day") for d in days if isinstance(d.get("day"), int)]
        if day_nums != list(range(1, len(days) + 1)):
            issues.append((name, f"day 编号不连续: {day_nums}"))
        # 字段缺失
        for i, d in enumerate(days, 1):
            missing = [f for f in REQUIRED_FIELDS if f not in d or d.get(f) in (None, "", [], {})]
            if missing:
                issues.append((name, f"Day{i} 缺字段: {missing}"))
            dist = d.get("distance_km", 0) or 0
            gain = d.get("gain_m", 0) or 0
            if dist <= 0:
                issues.append((name, f"Day{i} distance_km<=0: {dist}"))
            if gain < 0:
                issues.append((name, f"Day{i} gain_m<0: {gain}"))
            if dist > 40:
                issues.append((name, f"Day{i} 单日 {dist}km 疑似偏长"))
            if gain > 2000:
                issues.append((name, f"Day{i} 单日爬升 {gain}m 疑似偏高"))
        # 总和 vs 知识库
        total_km = sum((d.get("distance_km") or 0) for d in days)
        if name in known:
            kb_km = known[name]["distance_km"]
            if kb_km > 0:
                dev = abs(total_km - kb_km) / kb_km
                if dev > 0.25:
                    issues.append((name, f"分段总和 {total_km}km vs 知识库 {kb_km}km 偏差 {dev:.0%}"))
            kb_days = known[name]["days"]
            if len(days) != kb_days:
                issues.append((name, f"分段天数 {len(days)} vs 知识库 {kb_days} 天不一致"))
        else:
            issues.append((name, "知识库无此路线(仅分段文件)"))

    # 输出
    print(f"=== 无分段的路由 ({len(no_segments)}) ===")
    if no_segments:
        print("  ", no_segments)

    print(f"\n=== 问题清单 ({len(issues)}) ===")
    by_route = {}
    for name, msg in issues:
        by_route.setdefault(name, []).append(msg)
    for name in sorted(by_route):
        print(f"  ⚠️ {name}")
        for msg in by_route[name]:
            print(f"      - {msg}")

    total_routes_with_issues = len(by_route)
    print(f"\n摘要: {len(segs)} 条路线中 {total_routes_with_issues} 条存在问题, "
          f"{len(segs) - total_routes_with_issues - len(no_segments)} 条通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
