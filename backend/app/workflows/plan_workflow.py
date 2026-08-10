"""
LangGraph 工作流 — 多 Agent 协作的徒步规划流程

流程:
  START → Orchestrator → RouteAnalyst ─┬─→ EquipmentPlanner → EquipmentReviewer ─┐
                                        └─→ SafetyAssessor ──────────────────────┤
                                                                                  ↓
                                                                    Synthesizer → END

装备审核不通过时: EquipmentReviewer → EquipmentPlanner (重新规划)
安全高风险时: 整个流程提前结束并警告
"""
from dataclasses import dataclass, field
from typing import Any
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """工作流状态 — 在 Agent 之间传递的上下文"""
    # 用户输入
    user_input: str = ""
    user_id: int = 0
    plan_id: int = 0

    # 路线数据
    route_data: dict = field(default_factory=dict)
    route_done: bool = False

    # 装备数据
    equipment_data: dict = field(default_factory=dict)
    equipment_review: dict = field(default_factory=dict)
    equipment_done: bool = False
    equipment_approved: bool = False

    # 安全数据
    safety_data: dict = field(default_factory=dict)
    safety_done: bool = False
    safety_go: bool = True

    # 结果
    final_plan: dict = field(default_factory=dict)
    completed: bool = False
    cancelled: bool = False

    # 日志
    agent_logs: list[dict] = field(default_factory=list)
    current_stage: str = "init"

    # 重试
    equipment_retry_count: int = 0
    max_retries: int = 3


async def run_plan_workflow(
    user_input: str,
    user_id: int,
    plan_id: int,
    context: dict | None = None,
    on_log: callable = None,
) -> dict:
    """
    执行多 Agent 协作徒步规划工作流。

    Args:
        user_input: 用户原始输入
        user_id: 用户 ID
        plan_id: 规划方案 ID
        context: 额外上下文（已选路线等）
        on_log: 日志回调函数，用于 SSE 推送

    Returns:
        最终规划方案 (dict)
    """
    state = WorkflowState(
        user_input=user_input,
        user_id=user_id,
        plan_id=plan_id,
    )

    if context:
        state.route_data = context.get("route_data", {})

    # Agent role mapping
    _agent_roles = {
        "Orchestrator": "orchestrator",
        "RouteAnalyst": "planner",
        "WeatherService": "planner",
        "MealPlanner": "planner",
        "EquipmentPlanner": "planner",
        "EquipmentReviewer": "reviewer",
        "SafetyAssessor": "reviewer",
        "Synthesizer": "synthesizer",
    }

    async def log_event(agent_name: str, status: str, data: dict):
        """记录并推送 Agent 事件"""
        event = {
            "agent_name": agent_name,
            "role": _agent_roles.get(agent_name, "planner"),
            "status": status,
            "output": data.get("output", {}),
            "thinking": data.get("thinking", ""),
            "input": data.get("input", data.get("message", "")),
        }
        state.agent_logs.append(event)
        state.current_stage = agent_name
        logger.info(f"[Workflow] {agent_name}: {status}")
        if on_log:
            await on_log(event)

    # ===== 极速工作流：1次LLM调用 =====
    # Phase 1 (并行，知识库+规则，秒级): RouteAnalyst + EquipmentPlanner
    # Phase 2 (规则引擎，秒级): EquipmentReviewer + SafetyAssessor
    # Phase 3 (唯一LLM): Synthesizer — 融合所有数据，个性化汇总
    #
    # 路线用知识库匹配（已有8条热门路线），装备用规则生成（13个分类）。
    # 只保留 1 次 LLM 调用做最终汇总，目标 15-20s。

    from app.agents.route_analyst import RouteAnalystAgent
    from app.agents.equipment_planner import EquipmentPlannerAgent
    from app.agents.equipment_reviewer import EquipmentReviewerAgent
    from app.agents.safety_assessor import SafetyAssessorAgent
    from app.agents.synthesizer import SynthesizerAgent
    import time as _time

    # ---- Phase 1: RouteAnalyst → Weather → EquipmentPlanner 串行 ----
    route_agent = RouteAnalystAgent()
    equip_agent = EquipmentPlannerAgent()

    # Step 1: 路线分析（知识库优先，未命中则 LLM）
    await log_event("RouteAnalyst", "running", {"message": "分析路线..."})
    t0 = _time.time()

    if state.route_data.get("distance_km"):
        route_data = state.route_data
        route_thinking = ""
    else:
        route_result = await route_agent.think(user_input, {"route_data": state.route_data})
        route_data = route_result.output if route_result.success else {}
        route_thinking = route_result.thinking

    state.route_data = route_data
    state.route_done = True
    is_known = route_data.get("distance_km", 0) > 0 and "message" not in route_data

    await log_event("RouteAnalyst", "completed", {
        "output": route_data,
        "thinking": route_thinking,
    })

    # Step 2: 天气查询（真实 API，秒级）
    weather_data = {}
    from app.services.route_coords import get_route_coords
    from app.services.weather_service import fetch_weather, get_hiking_weather_advice

    route_name = route_data.get("name", "")
    coords = get_route_coords(route_name)
    if not coords and route_data.get("trailhead"):
        # 尝试用 trailhead 匹配
        coords = get_route_coords(route_data["trailhead"])

    if coords:
        await log_event("WeatherService", "running", {"message": f"获取 {route_name} 天气..."})
        start_date = (context or {}).get("start_date")
        weather_data = await fetch_weather(coords[0], coords[1],
            days=route_data.get("duration_days", 3) + 2,
            start_date=start_date)
        weather_advice = get_hiking_weather_advice(weather_data)
        weather_data["hiking_advice"] = weather_advice
        await log_event("WeatherService", "completed", {
            "output": {
                "summary": weather_data.get("summary", ""),
                "has_severe": weather_data.get("has_severe", False),
            },
            "thinking": f"坐标 ({coords[0]:.2f}, {coords[1]:.2f}) 天气获取成功",
        })
    else:
        logger.info(f"[Workflow] 未找到路线 '{route_name}' 的坐标，跳过天气查询")
        await log_event("WeatherService", "completed", {
            "output": {"summary": "无坐标数据，跳过天气查询"},
        })

    # Step 3: 装备（规则引擎秒出，个性化交给 Synthesizer）
    await log_event("EquipmentPlanner", "running", {"message": "匹配装备方案..."})
    equip_data = await equip_agent._execute_with_tools(user_input, {"route_data": route_data})
    equip_thinking = equip_agent._generate_thinking(user_input, {"route_data": route_data})
    state.equipment_data = equip_data

    await log_event("EquipmentPlanner", "completed", {
        "output": equip_data, "thinking": equip_thinking,
    })
    t1 = _time.time()
    logger.info(f"[Workflow] Phase 1 完成（{'知识库' if is_known else 'LLM查询'}路线 + 天气 + 装备），耗时 {t1-t0:.1f}s")

    # ---- Phase 2: EquipmentReviewer + SafetyAssessor（规则引擎，秒级）----
    reviewer = EquipmentReviewerAgent()
    safety_agent = SafetyAssessorAgent()

    await log_event("EquipmentReviewer", "running", {"message": "审核装备..."})
    review_data = await reviewer._execute_with_tools(user_input, {
        "equipment_data": equip_data, "route_data": route_data,
    })
    state.equipment_review = review_data
    state.equipment_done = True
    state.equipment_approved = review_data.get("result") == "approved"
    await log_event("EquipmentReviewer", "completed", {
        "output": review_data,
        "thinking": reviewer._generate_thinking(user_input, {}),
    })

    await log_event("SafetyAssessor", "running", {"message": "评估安全..."})
    safety_data = await safety_agent._execute_with_tools(user_input, {
        "route_data": route_data,
        "equipment_review": review_data,
        "weather_data": weather_data,
    })
    state.safety_data = safety_data
    state.safety_done = True
    state.safety_go = safety_data.get("go_nogo", "conditional_go") != "no_go"
    await log_event("SafetyAssessor", "completed", {
        "output": safety_data,
        "thinking": safety_agent._generate_thinking(user_input, {}),
    })

    t2 = _time.time()
    logger.info(f"[Workflow] Phase 2 完成 (规则引擎)，耗时 {t2-t1:.1f}s")

    # ---- Phase 2.5: 路餐推荐（知识库，秒级）----
    meal_data = {}
    try:
        from app.services.meal_service import recommend_meals
        # 从用户输入提取预算偏好
        budget = "标准"
        if any(w in user_input for w in ["省钱", "经济", "穷游", "预算有限", "便宜"]):
            budget = "经济"
        elif any(w in user_input for w in ["吃好", "高端", "讲究", "不差钱", "品质"]):
            budget = "高端"

        route_days = route_data.get("duration_days", 2)
        route_ele = route_data.get("max_elevation_m", 0)
        season = weather_data.get("daily", [{}])[0] if weather_data.get("daily") else {}
        season_str = "夏季" if (season.get("temp_max_c", 10) or 10) > 28 else (
            "冬季" if (season.get("temp_min_c", 0) or 0) < 0 else "春秋季")

        meal_data = recommend_meals(
            days=route_days,
            budget=budget,
            route_elevation=route_ele,
            season=season_str,
        )
        await log_event("MealPlanner", "completed", {
            "output": {
                "budget_tier": meal_data.get("budget_tier"),
                "daily_count": len(meal_data.get("daily", [])),
                "estimated_cost": meal_data.get("estimated_cost_range"),
            },
            "thinking": f'为 {route_days} 天路线生成 {budget} 路餐计划',
        })
    except Exception as e:
        logger.warning(f"[Workflow] 路餐推荐失败: {e}")

    # ---- Phase 3: Synthesizer（唯一 LLM 调用）----
    await log_event("Synthesizer", "running", {"message": "AI 正在生成个性化徒步方案..."})
    synthesizer = SynthesizerAgent()
    synth_result = await synthesizer.think(user_input, {
        "route_data": state.route_data,
        "equipment_data": state.equipment_data,
        "equipment_review": state.equipment_review,
        "safety_data": state.safety_data,
        "weather_data": weather_data,
        "meal_data": meal_data,
    })

    if synth_result.success:
        state.final_plan = synth_result.output
        state.completed = True

    await log_event("Synthesizer", "completed" if synth_result.success else "failed", {
        "output": synth_result.output,
        "thinking": synth_result.thinking,
        "message": "🎉 徒步规划方案生成完成！",
    })

    # 返回最终结果
    return {
        "success": state.completed,
        "plan": state.final_plan,
        "agent_logs": state.agent_logs,
        "route_data": state.route_data,
        "equipment_data": state.equipment_data,
        "equipment_review": state.equipment_review,
        "safety_data": state.safety_data,
        "weather_data": weather_data,
        "meal_data": meal_data,
        "safety_go": state.safety_go,
        "equipment_approved": state.equipment_approved,
    }


def create_plan_workflow():
    """
    创建 LangGraph 工作流定义。

    在实际部署中使用 LangGraph StateGraph 来定义节点和边。
    当前版本使用函数式流程（run_plan_workflow）作为过渡。

    LangGraph 伪代码：
    ```python
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(WorkflowState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("route_analyst", route_analyst_node)
    workflow.add_node("equipment_planner", equipment_planner_node)
    workflow.add_node("equipment_reviewer", equipment_reviewer_node)
    workflow.add_node("safety_assessor", safety_assessor_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "route_analyst")
    workflow.add_edge("route_analyst", "equipment_planner")
    workflow.add_edge("route_analyst", "safety_assessor")
    workflow.add_edge("equipment_planner", "equipment_reviewer")
    workflow.add_edge("safety_assessor", "synthesizer")

    # 条件边：审核不通过则回退
    workflow.add_conditional_edges(
        "equipment_reviewer",
        decide_next,
        {
            "approved": "synthesizer",
            "retry": "equipment_planner",
            "rejected": "synthesizer",
        }
    )

    workflow.add_edge("equipment_reviewer", "synthesizer")
    workflow.add_edge("synthesizer", END)

    app = workflow.compile()
    ```
    """
    return run_plan_workflow
