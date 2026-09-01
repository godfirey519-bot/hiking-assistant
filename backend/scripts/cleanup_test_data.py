"""P1-3 测试数据温和清理（用户已确认范围 2026-08-28）。

删除:
  1. routes 表 id 1-3 的 'test' / 'test route' / 'test route 2' 占位路线
  2. trip_records 的 'test trip' (alice 的测试记录)
  3. man (user_id=4) 的 2 件 '新装备' 占位装备 (weight=0, 未填写)

保留: 全部用户、全部方案(plans/plan_sections/plan_agent_logs)、
      装备分类、背包表等。

用法: python scripts/cleanup_test_data.py
"""
import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select
from app.database import async_session
from app.models.gear import GearItem
from app.models.route import Route
from app.models.trip import TripRecord


async def cleanup() -> None:
    async with async_session() as db:
        # 1) 测试路线（按 id，最老的 3 条占位数据）
        routes = (await db.execute(select(Route).where(Route.id <= 3))).scalars().all()
        print(f"删除路线 {len(routes)} 条: {[(r.id, r.name) for r in routes]}")
        for r in routes:
            await db.delete(r)

        # 2) 'test trip' 测试行程
        trips = (await db.execute(select(TripRecord).where(TripRecord.title == "test trip"))).scalars().all()
        print(f"删除测试行程 {len(trips)} 条: {[t.title for t in trips]}")
        for t in trips:
            await db.delete(t)

        # 3) man 的 '新装备' 占位（weight=0 且未填写的占位行）
        placeholders = (await db.execute(
            select(GearItem).where(GearItem.name == "新装备", GearItem.user_id == 4)
        )).scalars().all()
        print(f"删除占位装备 {len(placeholders)} 件")
        for g in placeholders:
            await db.delete(g)

        await db.commit()
        print("✅ 清理完成")

        # 校验
        r_count = (await db.execute(select(Route))).scalars().all()
        t_count = (await db.execute(select(TripRecord))).scalars().all()
        g_count = (await db.execute(select(GearItem))).scalars().all()
        print(f"剩余: routes={len(r_count)} trip_records={len(t_count)} gear_items={len(g_count)}")


if __name__ == "__main__":
    asyncio.run(cleanup())
