"""方案分享 — 免登录只读分享链接

- POST /api/share/plans/{plan_id}  生成分享链接（需登录，本人方案）
- GET  /api/share/plans/{token}    免登录读取分享方案（只读）
- DELETE /api/share/plans/{token}  撤销分享（需登录，本人方案）
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, PlanSection, PlanAgentLog, PlanShare
from app.schemas.share import ShareCreateResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/share", tags=["分享"])

TOKEN_LENGTH = 24


def _plan_to_dict(plan: Plan) -> dict:
    """与 plans.py 一致的手动序列化（避免异步懒加载）"""
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
                "id": s.id, "plan_id": s.plan_id, "type": s.type, "title": s.title,
                "content": s.content or "{}", "agent_name": s.agent_name,
                "reviewed_by": s.reviewed_by, "review_result": s.review_result,
                "review_notes": s.review_notes,
            }
            for s in (plan.sections or [])
        ],
        "agent_logs": [
            {
                "id": log.id, "plan_id": log.plan_id, "agent_name": log.agent_name,
                "role": log.role, "status": log.status, "input": log.input or "",
                "output": log.output or "", "thinking": log.thinking or "",
                "started_at": log.started_at, "completed_at": log.completed_at,
            }
            for log in (plan.agent_logs or [])
        ],
    }


async def _load_plan(db: AsyncSession, plan_id: int) -> Plan | None:
    result = await db.execute(
        select(Plan)
        .options(selectinload(Plan.sections), selectinload(Plan.agent_logs))
        .where(Plan.id == plan_id)
    )
    return result.unique().scalar_one_or_none()


@router.post("/plans/{plan_id}", response_model=ShareCreateResponse)
async def create_share(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为本人方案生成分享链接（幂等：已有则复用）"""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "方案不存在")

    existing = await db.execute(select(PlanShare).where(PlanShare.plan_id == plan_id))
    share = existing.scalar_one_or_none()
    if not share:
        share = PlanShare(plan_id=plan_id, token=secrets.token_hex(TOKEN_LENGTH))
        db.add(share)
        await db.commit()
        await db.refresh(share)

    return ShareCreateResponse(
        token=share.token,
        url=f"/share/plans/{share.token}",
    )


@router.get("/plans/{token}")
async def get_shared_plan(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """免登录读取分享方案（只读）"""
    result = await db.execute(select(PlanShare).where(PlanShare.token == token))
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(404, "分享链接不存在或已撤销")

    plan = await _load_plan(db, share.plan_id)
    if not plan:
        raise HTTPException(404, "方案不存在或已删除")

    return {
        "shared_by": plan.user_id,
        "plan": _plan_to_dict(plan),
    }


@router.delete("/plans/{share_token}")
async def revoke_share(
    share_token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销分享（仅方案所有者）"""
    result = await db.execute(
        select(PlanShare).where(PlanShare.token == share_token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(404, "分享链接不存在")

    plan_result = await db.execute(select(Plan).where(Plan.id == share.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan or plan.user_id != user.id:
        raise HTTPException(403, "无权撤销该分享")

    await db.delete(share)
    return {"success": True}
