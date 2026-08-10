"""
将采集的路线 JSON 导入到 route_analyst.py 知识库
用法: python -m scripts.import_routes [--dry-run] [--input collected_routes.json]
"""
import json
import os
import sys
import re
import argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def format_route_entry(route: dict) -> str:
    """将路线 dict 格式化为 Python dict 字符串"""
    name = route.get("name", "未知")
    distance = route.get("distance_km", 20)
    gain = route.get("elevation_gain_m", 1000)
    max_ele = route.get("max_elevation_m", 3000)
    difficulty = route.get("difficulty", "中等")
    days = route.get("duration_days", 1)
    terrain = route.get("terrain", "未知")
    water = route.get("water_sources", "")
    season = route.get("best_season", "")
    trailhead = route.get("trailhead", "")
    notes = route.get("notes", "")
    region = route.get("region", "")

    lines = [
        f'    "{name}": {{',
        f'        "distance_km": {distance}, "elevation_gain_m": {gain}, "max_elevation_m": {max_ele},',
        f'        "difficulty": "{difficulty}", "duration_days": {days},',
        f'        "terrain": "{terrain}",',
        f'        "water_sources": "{water}",',
        f'        "best_season": "{season}",',
        f'        "trailhead": "{trailhead}",',
        f'        "notes": "{notes}",',
        f'    }},',
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只预览不写入")
    parser.add_argument("--input", default="data/collected_routes.json", help="采集 JSON 文件")
    args = parser.parse_args()

    input_path = os.path.join(os.path.dirname(__file__), "..", args.input)

    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        print("先运行: python -m scripts.batch_collect_routes")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    routes = data.get("routes", [])
    print(f"加载 {len(routes)} 条路线")

    if args.dry_run:
        print("\n===== 预览 =====")
        for r in routes:
            print(f"  {r['name']}: {r['distance_km']}km, {r['elevation_gain_m']}m, {r['difficulty']}, {r['duration_days']}天, {r.get('region','')}")
        return

    # 按区域分组
    regions = {}
    for r in routes:
        reg = r.get("region", "其他")
        if reg not in regions:
            regions[reg] = []
        regions[reg].append(r)

    # 生成代码片段
    code = "\n".join([
        format_route_entry(r) for r in routes
    ])

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "routes_to_import.py")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 自动采集的路线数据，审核后合并到 route_analyst.py\n")
        f.write(f"# 共 {len(routes)} 条，采集时间 {data.get('collected_at', 'unknown')}\n\n")
        f.write(code)

    print(f"\n生成代码片段: {output_path}")
    print(f"手动审核后，复制内容到 route_analyst.py 的 KNOWN_ROUTES 字典中")

    # 按区域统计
    print("\n===== 区域分布 =====")
    for reg, items in sorted(regions.items(), key=lambda x: -len(x[1])):
        print(f"  {reg}: {len(items)} 条")


if __name__ == "__main__":
    main()
