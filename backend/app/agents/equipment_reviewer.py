"""🧐 装备审核 Agent — 审核装备方案的合理性、安全性、重量"""
from app.agents.base import BaseAgent, AgentResult
import logging

logger = logging.getLogger(__name__)


class EquipmentReviewerAgent(BaseAgent):
    name = "EquipmentReviewer"
    role = "reviewer"
    description = "装备审核专家 Agent，审核装备规划 Agent 的方案并给出改进建议"
    llm_max_tokens: int = 1024  # 审核结果简洁

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "审核分析推理过程",
  "output": {
    "result": "approved|needs_modification|rejected",
    "score": 85,
    "issues": [
      {"severity": "high|medium|low", "category": "分类", "problem": "问题描述", "suggestion": "修改建议"}
    ],
    "weight_analysis": {"estimated_total_kg": 12.5, "target_kg": 14, "is_acceptable": true},
    "summary": "审核总结"
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是一位严格的装备审核专家，专门审核徒步装备方案的合理性。

## 审核标准
1. **安全完整性**: 保命装备（急救、照明、保暖）是否齐全？
2. **重量合理性**: 总重量是否在体重的20%以内？有无冗余？
3. **季节匹配**: 装备是否适合当前季节和海拔？
4. **路线适配**: 特殊路况（涉水/冰雪/悬崖）是否有对应装备？
5. **性价比**: 推荐品牌是否在合理价格范围？
6. **冗余检查**: 是否带了不必要的东西？

## 审核结果
- ✅ 通过：方案合理，无需修改
- ⚠️ 需修改：有小问题，补充/调整后可执行
- ❌ 不通过：有重大安全隐患或严重问题，必须重新规划

## 输出格式
```json
{
  "result": "approved|needs_modification|rejected",
  "score": 85,
  "issues": [
    {"severity": "high|medium|low", "category": "装备名称", "problem": "问题描述", "suggestion": "修改建议"}
  ],
  "weight_analysis": {"estimated_total_kg": 12.5, "target_kg": 14, "is_acceptable": true},
  "summary": "审核总结"
}
```
"""

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        equipment = (context or {}).get("equipment_data", {})
        route = (context or {}).get("route_data", {})

        issues = []
        score = 100

        # 安全检查
        categories_found = set()
        if equipment:
            for cat_items in (equipment.get("equipment_by_category", {})).values():
                for item in cat_items:
                    categories_found.add(item.get("category", ""))

        required_categories = ["睡眠系统", "照明", "急救", "导航通讯", "饮水"]
        for cat in required_categories:
            if cat not in categories_found:
                score -= 20
                issues.append({
                    "severity": "high",
                    "category": cat,
                    "problem": f"缺少关键安全装备类别: {cat}",
                    "suggestion": f"请确保 {cat} 类装备齐全",
                })

        # 重量检查（假设平均体重70kg）
        estimated_weight = {
            "睡眠系统": 3000,
            "炊具系统": 800,
            "服装": 2500,
            "鞋袜": 1200,
            "照明": 100,
            "急救": 300,
            "导航通讯": 500,
            "饮水": 2500,
            "食物": 2500,
            "工具": 600,
        }

        total_weight = sum(
            estimated_weight.get(cat, 500) for cat in categories_found
        ) if categories_found else 12000

        max_weight = 14000  # 70kg * 20%

        result = "approved"
        if total_weight > max_weight:
            score -= 15
            issues.append({
                "severity": "medium",
                "category": "整体重量",
                "problem": f"预估总重量 {total_weight/1000:.1f}kg 超过目标 {max_weight/1000:.1f}kg",
                "suggestion": "建议减少非必要装备，优先选择轻量化替代品",
            })
            result = "needs_modification"

        # 高海拔检查
        max_ele = route.get("max_elevation_m", 0)
        if max_ele > 3000:
            if "羽绒服" not in str(equipment):
                score -= 10
                issues.append({
                    "severity": "high",
                    "category": "服装",
                    "problem": f"海拔 {max_ele}m 需要羽绒服保暖",
                    "suggestion": "增加轻量羽绒服作为静态保暖层",
                })

        reasoning = f"""
🧐 [EquipmentReviewer] 审核装备方案...

📋 审核维度:
  1. ✅ 安全完整性 → {'通过' if score >= 80 else '不通过'}
  2. ⚖️ 重量分析 → 预估 {total_weight/1000:.1f}kg / 目标 {max_weight/1000:.1f}kg
  3. 🏔️ 路线适配 → {'需要' if max_ele > 3000 else '无需'}高海拔装备
  4. 🔄 冗余检查 → {'有冗余' if total_weight > max_weight else '合理'}

📊 综合评分: {score}/100
📝 结论: {'✅ 通过' if result == 'approved' else '⚠️ 需修改'}
"""

        return {
            "result": result,
            "score": score,
            "issues": issues,
            "weight_analysis": {
                "estimated_total_kg": round(total_weight / 1000, 1),
                "target_kg": round(max_weight / 1000, 1),
                "is_acceptable": total_weight <= max_weight,
            },
            "summary": reasoning,
        }

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        return """🧐 [EquipmentReviewer] 开始审核装备方案...

审核标准:
  1. 安全完整性 — 急救/照明/保暖是否齐全
  2. 重量控制 — 是否在体重20%以内
  3. 季节匹配 — 装备是否适合当前条件
  4. 路线适配 — 特殊地形装备是否到位
  5. 冗余检查 — 是否存在不必要的重复

正在逐项检查..."""
