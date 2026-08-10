from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import json
import asyncio
import logging

from app.database import get_db, async_session
from app.models.user import User
from app.models.plan import Plan, PlanAgentLog
from app.api.deps import get_current_user

router = APIRouter(prefix="/agents", tags=["AI Agent"])
logger = logging.getLogger(__name__)


@router.post("/start-planning/{plan_id}")
async def start_agent_planning(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发多 Agent 协作规划流程（后台异步执行）"""
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "规划不存在")

    # 更新状态
    plan.status = "planning"
    await db.commit()

    # 在后台异步执行 Agent 工作流
    asyncio.create_task(_run_planning_background(plan_id, user.id, plan.title, plan.description))

    return {"success": True, "plan_id": plan_id, "message": "Agent 规划已在后台启动"}


async def _run_planning_background(plan_id: int, user_id: int, title: str, description: str):
    """后台执行 Agent 规划工作流（使用独立的 DB session）"""
    from app.services.plan_service import execute_planning

    async with async_session() as db:
        try:
            # 获取 User（用于 execute_planning）
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                logger.error(f"[Background] 用户 {user_id} 不存在")
                return

            logger.info(f"[Background] 开始执行规划 #{plan_id}: {title}")
            await execute_planning(plan_id, user, db)
            logger.info(f"[Background] 规划 #{plan_id} 执行完成")

        except Exception as e:
            logger.error(f"[Background] 规划 #{plan_id} 执行失败: {e}", exc_info=True)
            try:
                # 标记规划失败
                result = await db.execute(select(Plan).where(Plan.id == plan_id))
                plan = result.scalar_one_or_none()
                if plan:
                    plan.status = "failed"
                    await db.commit()
            except Exception:
                pass


@router.get("/planning-stream/{plan_id}")
async def stream_agent_progress(
    plan_id: int,
    user: User = Depends(get_current_user),
):
    """SSE 实时推送 Agent 执行进度。每次查询建立新的 DB 连接。"""
    async def event_generator():
        import aiosqlite
        from app.config import BASE_DIR
        db_path = str(BASE_DIR / "data" / "hiking.db")
        last_count = 0
        while True:
            # 直接用 aiosqlite 建立新连接，完全绕过 SQLAlchemy 缓存
            async with aiosqlite.connect(db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM plan_agent_logs WHERE plan_id = ? ORDER BY id ASC",
                    (plan_id,)
                )
                rows = await cursor.fetchall()
                current_count = len(rows)

                if current_count != last_count:
                    last_count = current_count
                    log_data = [
                        {"id": r["id"], "agent_name": r["agent_name"], "role": r["role"],
                         "status": r["status"], "output": r["output"], "thinking": r["thinking"]}
                        for r in rows
                    ]
                    yield f"data: {json.dumps(log_data, ensure_ascii=False)}\n\n"

                # Synthesizer completed → done
                has_synth = any(r["agent_name"] == "Synthesizer" and r["status"] == "completed" for r in rows)
                all_done = bool(rows) and all(r["status"] in ("completed", "failed") for r in rows)
                if all_done and has_synth:
                    yield f"data: {json.dumps([{'type': 'done', 'plan_id': plan_id, 'status': 'completed'}], ensure_ascii=False)}\n\n"
                    return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
