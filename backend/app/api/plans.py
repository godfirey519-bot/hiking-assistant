from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, PlanSection, PlanAgentLog
from app.schemas.plan import PlanCreate, PlanResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/plans", tags=["规划"])


def _plan_to_dict(plan: Plan) -> dict:
    """手动将 Plan ORM 对象转为 dict，避免 async lazy-load 问题"""
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "route_id": plan.route_id,
        "title": plan.title,
        "description": plan.description or "",
        "status": plan.status,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "participants": plan.participants,
        "created_at": plan.created_at,
        "sections": [
            {
                "id": s.id,
                "plan_id": s.plan_id,
                "type": s.type,
                "title": s.title,
                "content": s.content or "{}",
                "agent_name": s.agent_name,
                "reviewed_by": s.reviewed_by,
                "review_result": s.review_result,
                "review_notes": s.review_notes,
            }
            for s in (plan.sections or [])
        ],
        "agent_logs": [
            {
                "id": log.id,
                "plan_id": log.plan_id,
                "agent_name": log.agent_name,
                "role": log.role,
                "status": log.status,
                "input": log.input or "",
                "output": log.output or "",
                "thinking": log.thinking or "",
                "started_at": log.started_at,
                "completed_at": log.completed_at,
            }
            for log in (plan.agent_logs or [])
        ],
    }


@router.get("/")
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.sections), selectinload(Plan.agent_logs))
        .where(Plan.user_id == user.id)
        .order_by(Plan.created_at.desc())
    )
    plans = result.unique().scalars().all()
    return [_plan_to_dict(p) for p in plans]


@router.post("/")
async def create_plan(
    data: PlanCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = Plan(
        user_id=user.id,
        title=data.title,
        description=data.description,
        route_id=data.route_id,
        participants=data.participants,
        start_date=datetime.fromisoformat(data.start_date) if data.start_date else None,
        end_date=datetime.fromisoformat(data.end_date) if data.end_date else None,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    # New plan has no children - return directly without accessing lazy relationships
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "route_id": plan.route_id,
        "title": plan.title,
        "description": plan.description or "",
        "status": plan.status,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "participants": plan.participants,
        "created_at": plan.created_at,
        "sections": [],
        "agent_logs": [],
    }


@router.get("/{plan_id}")
async def get_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.sections), selectinload(Plan.agent_logs))
        .where(Plan.id == plan_id, Plan.user_id == user.id)
    )
    plan = result.unique().scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "规划不存在")
    return _plan_to_dict(plan)


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "规划不存在")
    await db.delete(plan)
    return {"success": True}
