"""🛡️ 安全评估 Agent — 综合评估徒步计划的安全性"""
from app.agents.base import BaseAgent, AgentResult
from app.agents.tools.weather_tools import check_weather, assess_weather_risk
import logging

logger = logging.getLogger(__name__)


class SafetyAssessorAgent(BaseAgent):
    name = "SafetyAssessor"
    role = "reviewer"
    description = "安全评估专家 Agent，综合评估路线、天气、装备、体能的安全性"

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "安全评估的推理过程",
  "output": {
    "overall_risk": "low|medium|high|extreme",
    "risk_score": 35,
    "risks": [
      {"category": "天气|高海拔|地形|装备|体能", "detail": "风险描述", "factors": ["具体因素"], "score_impact": 5}
    ],
    "mitigations": ["缓解措施"],
    "emergency_plan": {"nearest_hospital": "", "emergency_contact": "", "evacuation_routes": []},
    "go_nogo": "go|conditional_go|no_go"
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是一位徒步安全评估专家。安全永远是第一优先级。

## 评估维度
1. **天气风险**: 降雨、大风、雷电、高温/低温、能见度
2. **地形风险**: 陡坡、悬崖、涉水、落石、雪崩、冰裂缝
3. **装备风险**: 关键装备缺失或不适配
4. **体能风险**: 路线难度是否匹配用户的体能水平
5. **应急准备**: 撤退路线、救援联系方式、通讯保障
6. **高原风险**: 高反预防和应对（海拔>3000m）

## 风险等级
- 🟢 低风险: 正常出行
- 🟡 中等风险: 可出行，需做好充分准备
- 🟠 高风险: 建议调整计划或推迟
- 🔴 极高风险: 强烈建议取消

## 输出格式
```json
{
  "overall_risk": "low|medium|high|extreme",
  "risk_score": 35,
  "risks": [...],
  "mitigations": [...],
  "emergency_plan": {...},
  "go_nogo": "go|conditional_go|no_go"
}
```
"""

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        route = (context or {}).get("route_data", {})
        equipment_review = (context or {}).get("equipment_review", {})

        risks = []
        risk_score = 0

        # 1. 天气风险评估
        weather = await check_weather(route.get("trailhead", "未知地点"))
        weather_risk = assess_weather_risk(weather)
        if weather_risk["risk_score"] > 0:
            risks.append({
                "category": "天气",
                "detail": weather_risk["advice"],
                "factors": weather_risk["risks"],
                "score_impact": weather_risk["risk_score"],
            })
            risk_score += weather_risk["risk_score"]

        # 2. 地形风险评估
        difficulty = route.get("difficulty", "中等")
        difficulty_scores = {"轻松": 0, "较易": 1, "中等": 3, "较难": 5, "困难": 8, "专业级": 12}
        risk_score += difficulty_scores.get(difficulty, 3)

        if route.get("max_elevation_m", 0) > 3500:
            risks.append({
                "category": "高海拔",
                "detail": f"最高海拔 {route['max_elevation_m']}m，存在高反风险",
                "factors": ["高反症状（头痛/恶心/失眠）", "可能需要预留适应时间"],
                "score_impact": 5,
            })
            risk_score += 5

        # 3. 装备安全检查
        if equipment_review.get("result") == "rejected":
            risks.append({
                "category": "装备",
                "detail": "装备方案审核未通过，存在安全隐患",
                "factors": [f"评分: {equipment_review.get('score', 0)}/100"],
                "score_impact": 10,
            })
            risk_score += 10
        elif equipment_review.get("result") == "needs_modification":
            risks.append({
                "category": "装备",
                "detail": "装备方案需要修改，部分项目不达标",
                "factors": [f"评分: {equipment_review.get('score', 0)}/100"],
                "score_impact": 5,
            })
            risk_score += 5

        # 4. 综合判定
        thresholds = [
            (15, "low", "go"),
            (30, "medium", "conditional_go"),
            (50, "high", "conditional_go"),
            (100, "extreme", "no_go"),
        ]

        overall_risk = "low"
        go_nogo = "go"
        for threshold, level, decision in thresholds:
            if risk_score > threshold:
                overall_risk = level
                go_nogo = decision

        return {
            "overall_risk": overall_risk,
            "risk_score": risk_score,
            "risks": risks,
            "weather": weather,
            "weather_risk": weather_risk,
            "mitigations": [
                "出发前检查天气预报，恶劣天气取消行程",
                "告知家人/朋友行程计划和预计返回时间",
                "携带充足的水和食物（至少多1天量）",
                "手机下载离线地图并充满电",
                "了解最近的撤离路线和救援电话",
            ],
            "emergency_plan": {
                "nearest_hospital": "（需根据路线查询）",
                "emergency_contact": "110/120，山区可能无信号",
                "evacuation_routes": ["原路返回（首选）"],
                "communication": "手机+充电宝，无信号区建议卫星设备",
            },
            "go_nogo": go_nogo,
        }

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        return """🛡️ [SafetyAssessor] 开始综合安全评估...

评估维度:
  🔵 天气风险 → 查询天气预报，评估降水/风速/温度
  🔵 地形风险 → 基于路线数据评估陡坡/悬崖/高海拔
  🔵 装备风险 → 结合装备审核结果
  🔵 体能风险 → 对比路线难度与用户水平
  🔵 应急准备 → 撤退路线/救援/通讯

正在逐一评估..."""
