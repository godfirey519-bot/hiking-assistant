"""🎯 主控 Orchestrator Agent — 分解任务、调度其他 Agent、汇总结果"""
from app.agents.base import BaseAgent, AgentResult
import json
import logging

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    name = "Orchestrator"
    role = "orchestrator"
    description = "徒步规划主控 Agent，负责理解用户意图、分解任务、调度专业 Agent、汇总最终方案"
    llm_max_tokens: int = 1024  # 只需输出任务分解，快速完成

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "详细的需求分析和任务分解推理过程",
  "output": {
    "user_intent": "简洁描述理解到的用户意图",
    "tasks": [
      {"agent": "Agent名称", "priority": 1, "input": "给该Agent的输入", "depends_on": []}
    ],
    "execution_plan": "并行/串行的执行说明",
    "key_questions": ["需要向用户确认的关键问题"]
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是一个徒步规划专家团队的协调者（Orchestrator）。

## 你的职责
1. **理解需求**: 分析用户的徒步意图——目的地、时间、人数、经验水平、已有装备
2. **任务分解**: 将用户需求分解为子任务，分配给对应的专业 Agent
3. **协调执行**: 决定 Agent 的执行顺序和并行策略
4. **冲突解决**: 当审核 Agent 发现问题时，协调规划 Agent 进行调整
5. **质量把控**: 确保最终方案的完整性和可行性

## 可调度的 Agent 团队

| Agent | 专长 | 何时调度 |
|-------|------|---------|
| RouteAnalyst | 路线分析、GPX解析、难度评估 | 用户提到具体路线或上传GPX |
| EquipmentPlanner | 装备推荐、重量计算、品牌建议 | 需要装备清单 |
| EquipmentReviewer | 审核装备方案合理性 | 装备规划完成后必须审核 |
| SafetyAssessor | 安全风险评估（天气/地形/装备） | 所有规划都必须经过安全评估 |
| Synthesizer | 汇总所有 Agent 输出，生成最终方案 | 所有其他 Agent 完成后 |

## 输出格式
以 JSON 格式输出任务分解方案：
```json
{
  "user_intent": "简洁描述理解到的用户意图",
  "tasks": [
    {"agent": "Agent名称", "priority": 1, "input": "给该Agent的输入", "depends_on": []},
    ...
  ],
  "execution_plan": "并行/串行的执行说明",
  "key_questions": ["需要向用户确认的关键问题"]
}
```
"""

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        """分析用户需求并生成任务分解"""
        lines = [
            "🎯 [Orchestrator] 开始分析用户需求...",
            "",
            "📋 需求理解:",
            f"  - 用户原始输入: \"{user_input[:200]}\"",
        ]

        # 识别关键信息
        if any(w in user_input for w in ["武功山", "黄山", "雨崩", "虎跳峡", "四姑娘", "太白", "徒步"]):
            lines.append("  - 检测到具体目的地提及")
            lines.append("  → 调度 RouteAnalyst 获取路线数据")

        if any(w in user_input for w in ["装备", "背包", "带", "准备", "买", "推荐"]):
            lines.append("  - 检测到装备相关需求")
            lines.append("  → 调度 EquipmentPlanner 制定装备方案")

        if any(w in user_input for w in ["天", "夜", "日", "国庆", "五一", "周末"]):
            lines.append("  - 检测到时间/日期信息")
            lines.append("  → 需要考虑季节因素")

        if any(w in user_input for w in ["新手", "第一次", "初级", "入门"]):
            lines.append("  - 检测到用户经验水平: 新手")
            lines.append("  → 装备和安全建议需要更加保守")

        lines.extend([
            "",
            "🔄 任务分解:",
            "  1. [RouteAnalyst] 分析路线 - 获取距离/爬升/难度",
            "  2. [EquipmentPlanner] 装备推荐 - 基于路线+个人背包",
            "  3. [EquipmentReviewer] 装备审核 - 检查合理性",
            "  4. [SafetyAssessor] 安全评估 - 综合风险分析",
            "  5. [Synthesizer] 生成最终方案",
            "",
            "⚡ 执行策略:",
            "  - 阶段1: RouteAnalyst 先执行（其他 Agent 依赖路线数据）",
            "  - 阶段2: EquipmentPlanner 和 SafetyAssessor 并行执行",
            "  - 阶段3: EquipmentReviewer 审核装备方案",
            "  - 阶段4: 如有问题回退调整，否则 Synthesizer 汇总",
            "",
            "✅ 任务分解完成，开始调度执行...",
        ])

        return "\n".join(lines)

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        """生成任务分解方案"""
        return {
            "user_intent": user_input,
            "tasks": [
                {"agent": "RouteAnalyst", "priority": 1, "depends_on": []},
                {"agent": "EquipmentPlanner", "priority": 2, "depends_on": ["RouteAnalyst"]},
                {"agent": "EquipmentReviewer", "priority": 3, "depends_on": ["EquipmentPlanner"]},
                {"agent": "SafetyAssessor", "priority": 2, "depends_on": ["RouteAnalyst"]},
                {"agent": "Synthesizer", "priority": 4, "depends_on": ["EquipmentReviewer", "SafetyAssessor"]},
            ],
            "execution_plan": "先执行 RouteAnalyst → 再并行执行 EquipmentPlanner + SafetyAssessor → EquipmentReviewer 审核 → Synthesizer 汇总",
        }
