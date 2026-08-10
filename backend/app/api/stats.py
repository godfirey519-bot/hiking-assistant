"""Dashboard 统计接口 — 一次返回首页所需全部数据"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json
import os

from app.database import get_db
from app.models.user import User
from app.models.route import Route
from app.models.gear import GearItem
from app.models.trip import TripRecord
from app.models.plan import Plan
from app.api.deps import get_current_user

router = APIRouter(prefix="/stats", tags=["统计"])

# 路线知识库文件（与 route_analyst 同源）
_KB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "route_segments.json")


def _kb_route_count() -> int:
    """返回路线知识库中的路线数（route_segments.json 条数）"""
    try:
        if os.path.exists(_KB_FILE):
            with open(_KB_FILE, "r", encoding="utf-8") as f:
                return len(json.load(f))
    except Exception:
        pass
    return 0


@router.get("/")
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """返回首页统计：知识库路线、我的路线、装备、记录、规划 + 最近规划"""
    user_routes = (
        await db.execute(
            select(func.count()).select_from(Route).where(Route.user_id == user.id)
        )
    ).scalar() or 0
    gear_items = (
        await db.execute(
            select(func.count()).select_from(GearItem).where(GearItem.user_id == user.id)
        )
    ).scalar() or 0
    trips = (
        await db.execute(
            select(func.count()).select_from(TripRecord).where(TripRecord.user_id == user.id)
        )
    ).scalar() or 0
    plans = (
        await db.execute(
            select(func.count()).select_from(Plan).where(Plan.user_id == user.id)
        )
    ).scalar() or 0

    # 最近规划（前 5 条，仅取列表字段，避免 async lazy-load）
    result = await db.execute(
        select(Plan)
        .where(Plan.user_id == user.id)
        .order_by(Plan.created_at.desc())
        .limit(5)
    )
    recent_plans = [
        {
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in result.scalars().all()
    ]

    return {
        "kb_routes": _kb_route_count(),
        "user_routes": user_routes,
        "gear_items": gear_items,
        "trips": trips,
        "plans": plans,
        "recent_plans": recent_plans,
    }
