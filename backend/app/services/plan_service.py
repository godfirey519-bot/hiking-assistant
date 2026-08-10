"""规划服务 — 将 Agent 工作流接入数据库操作"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.plan import Plan, PlanSection, PlanAgentLog
from app.models.user import User
from app.workflows.plan_workflow import run_plan_workflow

logger = logging.getLogger(__name__)


async def execute_planning(
    plan_id: int,
    user: User,
    db: AsyncSession,
    route_data: dict | None = None,
) -> dict:
    """
    执行多 Agent 规划流程，并将结果存入数据库。

    通过回调函数实时更新 Agent 执行日志，支持前端 SSE 轮询。
    """
    # 获取规划
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return {"error": "规划不存在"}

    plan.status = "planning"
    await db.commit()

    # 日志回调：写入数据库并立即提交（让 SSE 能实时读到）
    async def db_log_callback(event: dict):
        try:
            log = PlanAgentLog(
                plan_id=plan_id,
                agent_name=event["agent_name"],
                role=event.get("role", "planner"),
                status=event["status"],
                input=json.dumps(event.get("input", {}), ensure_ascii=False),
                output=json.dumps(event.get("output", {}), ensure_ascii=False),
                thinking=event.get("thinking", ""),
            )
            db.add(log)
            await db.commit()
        except Exception as e:
            logger.error(f"日志写入失败: {e}")
            await db.rollback()

    # 执行工作流
    workflow_result = await run_plan_workflow(
        user_input=f"{plan.title} — {plan.description}",
        user_id=user.id,
        plan_id=plan_id,
        context={
            "route_data": route_data or {},
            "start_date": str(plan.start_date) if plan.start_date else None,
        },
        on_log=db_log_callback,
    )

    if workflow_result.get("success"):
        # 用原始 Agent 数据保存各部分——比 Synthesizer 二手汇总更准确完整
        route_data = workflow_result.get("route_data", {})
        equip_data = workflow_result.get("equipment_data", {})
        safety_data = workflow_result.get("safety_data", {})
        final_plan = workflow_result.get("plan", {})
        review_data = workflow_result.get("equipment_review", {})
        weather_data = workflow_result.get("weather_data", {})
        meal_data = workflow_result.get("meal_data", {})

        # 路线（原始数据）
        if route_data:
            db.add(PlanSection(plan_id=plan_id, type="route", title="路线分析",
                content=json.dumps(route_data, ensure_ascii=False), agent_name="RouteAnalyst"))

        # 装备（原始数据，含按分类的完整列表）
        if equip_data:
            # 确保装备数据包含审核结果
            equip_with_review = dict(equip_data)
            equip_with_review["review_result"] = review_data.get("result", "pending")
            equip_with_review["review_score"] = review_data.get("score", 0)
            equip_with_review["weight_analysis"] = review_data.get("weight_analysis", {})
            db.add(PlanSection(plan_id=plan_id, type="equipment", title="装备清单",
                content=json.dumps(equip_with_review, ensure_ascii=False),
                agent_name="EquipmentPlanner", reviewed_by="EquipmentReviewer",
                review_result=review_data.get("result"),
                review_notes=json.dumps(review_data.get("issues", []), ensure_ascii=False)))

        # 安全（原始数据）
        if safety_data:
            db.add(PlanSection(plan_id=plan_id, type="safety", title="安全评估",
                content=json.dumps(safety_data, ensure_ascii=False), agent_name="SafetyAssessor"))

        # 天气（真实 API 数据）
        if weather_data and weather_data.get("daily"):
            db.add(PlanSection(plan_id=plan_id, type="weather", title="天气预报",
                content=json.dumps(weather_data, ensure_ascii=False), agent_name="WeatherService"))

        # 路餐推荐
        if meal_data and meal_data.get("daily"):
            db.add(PlanSection(plan_id=plan_id, type="meal", title="路餐推荐",
                content=json.dumps(meal_data, ensure_ascii=False), agent_name="MealPlanner"))

        # 日程（取自 Synthesizer 的 LLM 输出，更个性化）
        schedule = final_plan.get("schedule", [])
        if not schedule:
            # Fallback: generate from route data
            days = route_data.get("duration_days", 2)
            dist = route_data.get("distance_km", 20)
            schedule = [{"day": i+1, "distance_km": round(dist/days,1),
                "description": f"第{i+1}天"} for i in range(days)]
        db.add(PlanSection(plan_id=plan_id, type="schedule", title="日程安排",
            content=json.dumps(schedule, ensure_ascii=False), agent_name="Synthesizer"))

        # 完整方案（Synthesizer LLM 生成的个性化汇总）
        if final_plan:
            db.add(PlanSection(plan_id=plan_id, type="summary", title="AI 徒步方案",
                content=json.dumps(final_plan, ensure_ascii=False), agent_name="Synthesizer"))

        plan.status = "completed"

    else:
        plan.status = "failed"

    await db.commit()
    return workflow_result
