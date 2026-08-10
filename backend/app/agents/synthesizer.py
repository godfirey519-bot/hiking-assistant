"""📝 综合汇总 Agent — 融合所有 Agent 输出，生成最终徒步方案"""
from app.agents.base import BaseAgent, AgentResult
import json
import logging

logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    name = "Synthesizer"
    role = "synthesizer"
    description = "综合汇总 Agent，融合所有专业 Agent 的输出，生成个性化徒步方案"
    llm_max_tokens: int = 2048  # 增加 token 以容纳个性化内容

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "方案汇总的融合推理过程（含用户画像分析和装备个性化调整依据）",
  "output": {
    "title": "徒步方案标题（含路线+天数）",
    "user_profile": {"experience": "", "season": "", "group": "", "concerns": [], "style": ""},
    "overview": {"destination": "", "distance_km": 0, "elevation_gain_m": 0, "difficulty": "", "duration_days": 0, "best_season": "", "trailhead": ""},
    "route_analysis": {},
    "equipment": {
      "by_category": {},
      "total_items": 0,
      "review_result": "",
      "review_score": 0,
      "weight_analysis": {},
      "personalized_adjustments": [{"category": "", "adjustment": "", "reason": ""}],
      "personalized_notes": "针对用户情况的装备总体建议"
    },
    "safety": {"overall_risk": "", "risk_score": 0, "risks": [], "mitigations": [], "go_nogo": ""},
    "schedule": [{"day": 1, "from": "起点", "to": "终点", "distance_km": 0, "gain_m": 0, "description": "", "morning": "", "afternoon": "", "evening": "", "terrain": "", "water": "", "highlights": "", "risks": "", "pace": "", "key_points": []}],
    "checklist": ["行前检查项（基于用户profile定制）"],
    "agents_involved": ["参与的Agent列表"]
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是资深徒步规划专家。根据路线数据、装备清单、安全评估、天气数据，为用户生成高度个性化的徒步方案JSON。

## 第一步：提取用户画像
从用户输入中提取以下信息（无法确定则用合理默认值）：
- experience: 徒步经验（新手/有经验/资深/专业）
- season: 出行季节（从输入中推断，如"国庆"→秋季10月，"五一"→春季5月）
- group: 队伍情况（单人/小团队/大队伍/亲子）
- concerns: 用户担忧点（如"第一次高原""担心高反""怕冷"等）
- style: 出行风格（轻量化/舒适型/摄影/赶路型）

## 第二步：装备个性化调整
基于用户画像，审视规则引擎生成的装备清单，做出以下调整：
1. 新手 → 增加急救用品、详细导航设备、备用电池
2. 高原路线 → 强调防晒/保暖/抗高反药品
3. 冬季/雨季 → 增加防水装备、保暖层、冰爪
4. 轻量化风格 → 建议超轻替代品、减少冗余
5. 摄影型 → 增加相机防护、三脚架建议、充电方案
6. 亲子 → 增加儿童相关装备、急救强化

在 personalized_adjustments 数组中对每项调整说明原因。

## 第三步：日程安排（极其重要！）

### 如果 route_data 中有 segments 字段→必须逐条使用！
- 每日的 from/to/distance_km/gain_m/terrain/water/highlights/risks/pace 必须来自 segments
- 你可以润色描述，但不能改数值、不能丢字段
- segments 的 day 字段对应日程的 day 字段，一一对应

### 如果 route_data 中没有 segments→自己生成
- 新手队伍：降低每日距离10-20%
- 摄影型：在风景点留出拍摄时间
- 赶路型：紧凑安排，最大化每日行进距离
- 匹配季节：夏季中午避暑，冬季缩短日间行进

### schedule 输出格式
每天必须包含: day, from, to, distance_km, gain_m, terrain, water, highlights, risks, pace, morning, afternoon, evening, description

## 第四步：安全提示定制
- 结合天气数据中的实际预报
- 针对用户经验水平给出相应警告
- 新手强调不冒险、高反症状识别等基础安全

## 输出要求
- 日程必须匹配 route_data.duration_days（天数不对是严重错误）
- 装备按原始数据输出，personalized_adjustments 作为补充
- 安全 risk_score 必须基于天气 + 路线 + 用户经验综合评估
- 使用中文"""


    async def think(self, user_input: str, context: dict | None = None) -> AgentResult:
        """LLM 汇总 + 后处理：强制合并分段数据到日程"""
        # 先用 LLM 生成
        result = await super().think(user_input, context)

        # 后处理：确保日程有详细数据
        if result.success:
            route_data = (context or {}).get("route_data", {})
            segments = route_data.get("segments", [])
            output = result.output if isinstance(result.output, dict) else {}

            if output:
                schedule = output.get("schedule", [])
                # 检查 LLM 是否生成了详细日程（有 from/to 字段）
                has_detail = any(s.get("from") and s.get("to") for s in (schedule or []))

                if segments:
                    # 有分段数据→强制合并
                    fixed_schedule = []
                    for seg in segments:
                        day_num = seg.get("day", len(fixed_schedule) + 1)
                        llm_day = next((s for s in schedule if s.get("day") == day_num), None)

                        seg_from = seg.get("from", "")
                        seg_to = seg.get("to", "")
                        seg_dist = seg.get("distance_km", 0)
                        seg_gain = seg.get("gain_m", 0)

                        entry = {
                            "day": day_num,
                            "from": seg_from or (llm_day.get("from", "") if llm_day else ""),
                            "to": seg_to or (llm_day.get("to", "") if llm_day else ""),
                            "distance_km": seg_dist or (llm_day.get("distance_km", 0) if llm_day else 0),
                            "gain_m": seg_gain or (llm_day.get("gain_m", 0) if llm_day else 0),
                            "terrain": seg.get("terrain", "") or (llm_day.get("terrain", "") if llm_day else ""),
                            "water": seg.get("water", "") or (llm_day.get("water", "") if llm_day else ""),
                            "highlights": seg.get("highlights", "") or (llm_day.get("highlights", "") if llm_day else ""),
                            "risks": seg.get("risks", "") or (llm_day.get("risks", "") if llm_day else ""),
                            "pace": seg.get("pace", "") or (llm_day.get("pace", "") if llm_day else ""),
                            "description": "第{}天: {} → {}，约{}km，爬升{}m".format(day_num, seg_from, seg_to, seg_dist, seg_gain),
                            "morning": (llm_day.get("morning", "") if llm_day else "") or "从{}出发".format(seg_from),
                            "afternoon": (llm_day.get("afternoon", "") if llm_day else "") or "到达{}".format(seg_to),
                            "evening": (llm_day.get("evening", "") if llm_day else "") or "扎营休息",
                            "key_points": (llm_day.get("key_points", []) if llm_day else []) or [seg.get("highlights", "")],
                        }
                        if llm_day and llm_day.get("notes"):
                            entry["notes"] = llm_day["notes"]
                        fixed_schedule.append(entry)

                    if len(fixed_schedule) < len(schedule):
                        for s in schedule:
                            if s.get("day", 0) > len(segments):
                                fixed_schedule.append(s)

                    output["schedule"] = fixed_schedule

                elif not has_detail:
                    # 无分段 + LLM 没生成详细日程 → 用改进的降级方法重新生成
                    from app.agents.base import AgentResult
                    fallback_output = await self._execute_with_tools(user_input, context)
                    if fallback_output and fallback_output.get("schedule"):
                        output["schedule"] = fallback_output["schedule"]
                    day_num = seg.get("day", len(fixed_schedule) + 1)
                    # 尝试找到 LLM 生成的对应天
                    llm_day = None
                    for s in (schedule or []):
                        if s.get("day") == day_num:
                            llm_day = s
                            break

                    seg_from = seg.get("from", "")
                    seg_to = seg.get("to", "")
                    seg_dist = seg.get("distance_km", 0)
                    seg_gain = seg.get("gain_m", 0)

                    entry = {
                        "day": day_num,
                        "from": seg_from or (llm_day.get("from", "") if llm_day else ""),
                        "to": seg_to or (llm_day.get("to", "") if llm_day else ""),
                        "distance_km": seg_dist or (llm_day.get("distance_km", 0) if llm_day else 0),
                        "gain_m": seg_gain or (llm_day.get("gain_m", 0) if llm_day else 0),
                        "terrain": seg.get("terrain", "") or (llm_day.get("terrain", "") if llm_day else ""),
                        "water": seg.get("water", "") or (llm_day.get("water", "") if llm_day else ""),
                        "highlights": seg.get("highlights", "") or (llm_day.get("highlights", "") if llm_day else ""),
                        "risks": seg.get("risks", "") or (llm_day.get("risks", "") if llm_day else ""),
                        "pace": seg.get("pace", "") or (llm_day.get("pace", "") if llm_day else ""),
                        "description": "第{}天: {} → {}，约{}km，爬升{}m".format(day_num, seg_from, seg_to, seg_dist, seg_gain),
                        "morning": (llm_day.get("morning", "") if llm_day else "") or "从{}出发".format(seg_from),
                        "afternoon": (llm_day.get("afternoon", "") if llm_day else "") or "到达{}".format(seg_to),
                        "evening": (llm_day.get("evening", "") if llm_day else "") or "扎营休息",
                        "key_points": (llm_day.get("key_points", []) if llm_day else []) or [seg.get("highlights", "")],
                    }
                    # 保留 LLM 生成的个性化 notes
                    if llm_day and llm_day.get("notes"):
                        entry["notes"] = llm_day["notes"]
                    fixed_schedule.append(entry)

                # 如果 segments 天数比 schedule 多出来的也加上
                if len(fixed_schedule) < len(schedule):
                    for s in schedule:
                        if s.get("day", 0) > len(segments):
                            fixed_schedule.append(s)

                output["schedule"] = fixed_schedule
                result.output = output

        return result

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        """融合所有 Agent 输出（LLM 不可用时的降级逻辑）"""
        route_data = (context or {}).get("route_data", {})
        equipment_data = (context or {}).get("equipment_data", {})
        equipment_review = (context or {}).get("equipment_review", {})
        safety_data = (context or {}).get("safety_data", {})
        weather_data = (context or {}).get("weather_data", {})

        # 提取用户画像（简单规则）
        profile = self._extract_profile(user_input)
        adjustments = self._generate_adjustments(profile, route_data, equipment_data)

        # 构建完整方案
        plan = {
            "title": f"{route_data.get('name', '未知路线')}徒步方案",
            "user_profile": profile,
            "overview": {
                "destination": route_data.get("name", "未知"),
                "distance_km": route_data.get("distance_km", 0),
                "elevation_gain_m": route_data.get("elevation_gain_m", 0),
                "difficulty": route_data.get("difficulty", "中等"),
                "duration_days": route_data.get("duration_days", 1),
                "best_season": route_data.get("best_season", "请自行查询"),
                "trailhead": route_data.get("trailhead", "未知"),
            },
            "route_analysis": route_data,
            "equipment": {
                "by_category": equipment_data.get("equipment_by_category", {}),
                "total_items": equipment_data.get("total_items", 0),
                "review_result": equipment_review.get("result", "pending"),
                "review_score": equipment_review.get("score", 0),
                "weight_analysis": equipment_review.get("weight_analysis", {}),
                "personalized_adjustments": adjustments,
                "personalized_notes": self._generate_gear_advice(profile, route_data),
            },
            "safety": {
                "overall_risk": safety_data.get("overall_risk", "unknown"),
                "risk_score": safety_data.get("risk_score", 0),
                "risks": safety_data.get("risks", []),
                "mitigations": safety_data.get("mitigations", []),
                "go_nogo": safety_data.get("go_nogo", "conditional_go"),
                "emergency_plan": safety_data.get("emergency_plan", {}),
            },
            "schedule": self._generate_schedule(route_data, profile),
            "checklist": self._generate_checklist(profile, route_data, weather_data),
            "agents_involved": [
                "RouteAnalyst → 路线数据分析",
                "WeatherService → 实时天气查询",
                "EquipmentPlanner → 装备方案制定",
                "EquipmentReviewer → 装备方案审核",
                "SafetyAssessor → 安全综合评估",
                "Synthesizer → 最终方案汇总",
            ],
        }

        return plan

    def _extract_profile(self, user_input: str) -> dict:
        """从用户输入中提取个人画像"""
        text = user_input.lower()
        profile = {
            "experience": "有经验",
            "season": "春秋季",
            "group": "小团队",
            "concerns": [],
            "style": "舒适型",
        }

        # 经验
        if any(w in text for w in ["新手", "第一次", "初次", "没经验", "小白"]):
            profile["experience"] = "新手"
        elif any(w in text for w in ["老驴", "资深", "专业", "多年"]):
            profile["experience"] = "资深"

        # 季节
        if any(w in text for w in ["国庆", "十一", "10月", "秋天", "秋季"]):
            profile["season"] = "秋季"
        elif any(w in text for w in ["五一", "5月", "春天", "春季"]):
            profile["season"] = "春季"
        elif any(w in text for w in ["暑假", "夏天", "夏季", "7月", "8月"]):
            profile["season"] = "夏季"
        elif any(w in text for w in ["春节", "寒假", "冬天", "冬季", "1月", "2月", "12月"]):
            profile["season"] = "冬季"

        # 团队
        if any(w in text for w in ["一个人", "单人", "独自", "solo"]):
            profile["group"] = "单人"
        elif any(w in text for w in ["大队伍", "团队", "多人", "公司"]):
            profile["group"] = "大队伍"
        elif any(w in text for w in ["亲子", "带孩子", "小朋友", "小孩"]):
            profile["group"] = "亲子"

        # 关注点
        if any(w in text for w in ["高反", "高原", "海拔"]):
            profile["concerns"].append("高原反应")
        if any(w in text for w in ["冷", "保暖", "防寒"]):
            profile["concerns"].append("低温保暖")
        if any(w in text for w in ["轻量", "轻量化", "轻装", "ul"]):
            profile["style"] = "轻量化"
            profile["concerns"].append("重量控制")
        if any(w in text for w in ["摄影", "拍照", "相机"]):
            profile["style"] = "摄影型"
        if any(w in text for w in ["赶路", "快速", "竞速"]):
            profile["style"] = "赶路型"

        return profile

    def _generate_adjustments(self, profile: dict, route: dict, equip: dict) -> list[dict]:
        """基于用户画像生成装备调整建议"""
        adjustments = []
        exp = profile.get("experience", "")
        season = profile.get("season", "")
        style = profile.get("style", "")
        concerns = profile.get("concerns", [])
        max_ele = route.get("max_elevation_m", 0)

        if exp == "新手":
            adjustments.append({
                "category": "安全装备",
                "adjustment": "增加卫星电话/卫星SOS设备",
                "reason": "新手遇险概率高，卫星通信是安全保障"
            })
            adjustments.append({
                "category": "导航",
                "adjustment": "建议双导航（手机+GPS手持机），并携带纸质地图",
                "reason": "新手容易迷路，多重导航保障更安全"
            })

        if max_ele > 3500:
            adjustments.append({
                "category": "药品",
                "adjustment": "必带乙酰唑胺（高原安）、布洛芬、葡萄糖",
                "reason": f"海拔{max_ele}m，高反风险高，需备抗高反药物"
            })

        if season == "冬季" or "低温保暖" in concerns:
            adjustments.append({
                "category": "服装",
                "adjustment": "增加羽绒服充绒量建议（200g+），携带备用羊毛袜2双",
                "reason": "冬季/低温环境，保暖是首要安全因素"
            })

        if style == "轻量化" or "重量控制" in concerns:
            adjustments.append({
                "category": "帐篷",
                "adjustment": "建议使用超轻帐篷（<1.5kg）或天幕+露营袋组合",
                "reason": "轻量化需求，减少背负重量"
            })

        if style == "摄影型":
            adjustments.append({
                "category": "电子设备",
                "adjustment": "建议携带充电宝20000mAh+，相机防水袋，迷你三脚架",
                "reason": "摄影需求，需保障设备供电和防护"
            })

        if profile.get("group") == "亲子":
            adjustments.append({
                "category": "急救",
                "adjustment": "增加儿童常用药（退烧、过敏、创可贴），儿童防晒霜",
                "reason": "亲子出行，儿童医疗需求需覆盖"
            })

        return adjustments

    def _generate_gear_advice(self, profile: dict, route: dict) -> str:
        """生成个性化装备总体建议"""
        parts = []
        exp = profile.get("experience", "")
        max_ele = route.get("max_elevation_m", 0)

        if exp == "新手":
            parts.append("作为新手，建议出发前在低难度路线试用装备1-2次，熟悉使用方法")
        if max_ele > 3000:
            parts.append(f"路线最高海拔{max_ele}m，务必提前1-2天到达适应海拔")
        if profile.get("style") == "轻量化":
            parts.append("轻量化出行需在安全与重量间平衡，关键装备（急救/保暖/导航）不可省略")

        return "；".join(parts) if parts else "请根据个人情况调整装备数量和品牌"

    def _generate_checklist(self, profile: dict, route: dict, weather: dict) -> list[str]:
        """生成个性化检查清单"""
        checklist = [
            "✅ 离线地图已下载",
            "✅ 充电宝充满电（建议20000mAh+）",
            "✅ 告知家人行程计划和预计返回时间",
            "✅ 购买户外保险（含直升机救援）",
        ]

        exp = profile.get("experience", "")
        max_ele = route.get("max_elevation_m", 0)
        season = profile.get("season", "")

        if exp == "新手":
            checklist.append("✅ 参加至少1次低难度拉练，测试体能和装备")
        if max_ele > 3000:
            checklist.append("✅ 提前到达适应海拔（建议提前1-2天）")
            checklist.append("✅ 携带抗高反药物（乙酰唑胺/红景天）")
        if season == "冬季" or max_ele > 4000:
            checklist.append("✅ 携带冰爪和雪套")
        if season == "夏季":
            checklist.append("✅ 携带充足饮水（3L+/天）+ 电解质粉")
        if profile.get("style") == "摄影型":
            checklist.append("✅ 相机电池充电 + 存储卡清空 + 防水袋")

        checklist.extend([
            "✅ 装备逐一检查（帐篷无破损、炉头能点火）",
            "✅ 急救包药品检查（注意有效期）",
            "✅ 食物和水充足（至少多备1天量）",
            "✅ 现金（山区可能无信号/无法手机支付）",
        ])

        return checklist

    def _generate_schedule(self, route: dict, profile: dict | None = None) -> list[dict]:
        """生成日程安排 — 优先使用路线知识库的分段数据"""
        segments = route.get("segments", [])
        exp = (profile or {}).get("experience", "有经验")
        style = (profile or {}).get("style", "舒适型")

        # 有分段数据 → 直接使用
        if segments:
            schedule = []
            for seg in segments:
                entry = {
                    "day": seg["day"],
                    "from": seg.get("from", ""),
                    "to": seg.get("to", ""),
                    "distance_km": seg.get("distance_km", 0),
                    "gain_m": seg.get("gain_m", 0),
                    "description": f'第{seg["day"]}天: {seg.get("from","")} → {seg.get("to","")}，约{seg.get("distance_km",0)}km',
                    "morning": f'从{seg.get("from","")}出发',
                    "afternoon": f'到达{seg.get("to","")}',
                    "evening": "扎营休息，补充能量",
                    "terrain": seg.get("terrain", ""),
                    "water": seg.get("water", ""),
                    "highlights": seg.get("highlights", ""),
                    "risks": seg.get("risks", ""),
                    "pace": seg.get("pace", ""),
                    "key_points": [seg.get("highlights", "")] if seg.get("highlights") else [],
                }
                if exp == "新手":
                    entry["notes"] = "新手注意控制节奏，多休息"
                schedule.append(entry)
            return schedule

        # 无分段数据 → 基于路线信息智能生成
        days = route.get("duration_days", 2)
        distance = route.get("distance_km", 20)
        gain = route.get("elevation_gain_m", 1000)
        max_ele = route.get("max_elevation_m", 3000)
        terrain = route.get("terrain", "")
        water = route.get("water_sources", "")
        season = route.get("best_season", "")
        trailhead = route.get("trailhead", "")
        notes = route.get("notes", "")
        route_name = route.get("name", "")

        speed_factor = 0.7 if exp == "新手" else (1.2 if style == "赶路型" else 1.0)
        dist_per_day = round((distance / max(days, 1)) * speed_factor, 1)
        gain_per_day = round(gain / max(days, 1))

        # Parse start/end from trailhead
        start = trailhead
        end = ""
        if "→" in trailhead:
            parts = trailhead.split("→")
            start = parts[0].strip()
            end = parts[-1].strip()
        elif "→" in notes:
            parts = notes.split("→")
            end = parts[-1].strip()[:20]

        schedule = []
        for day in range(days):
            is_first = day == 0
            is_last = day == days - 1

            # Estimate daily elevation
            day_ele = round(max_ele * (day + 1) / days) if not is_last else max_ele
            day_gain = gain_per_day

            # Generate from/to
            if is_first and start:
                day_from = start
            elif end and is_last:
                day_from = f"第{days-1}天营地"
            else:
                day_from = f"第{day}天营地"

            if is_last and end:
                day_to = end
            elif is_first:
                day_to = f"第{day+1}天营地"
            else:
                day_to = f"第{day+1}天营地" if not is_last else (end or "终点")

            # Terrain description
            terrain_parts = [t.strip() for t in terrain.split("、") if t.strip()]
            day_terrain = terrain_parts[day % len(terrain_parts)] if terrain_parts else terrain

            # Build entry with all available data
            entry = {
                "day": day + 1,
                "from": day_from,
                "to": day_to,
                "distance_km": dist_per_day,
                "gain_m": day_gain,
                "description": f"第{day+1}天: {day_from} → {day_to}，约{dist_per_day}km，爬升约{day_gain}m",
                "morning": f"从{day_from}出发，早餐后开始徒步",
                "afternoon": f"预计下午到达{day_to}",
                "evening": f"在{day_to}附近扎营休息" + ("，检查身体状况" if max_ele > 3000 else ""),
                "terrain": day_terrain if day_terrain else terrain,
                "water": water if water else "自备充足饮水",
                "pace": f"约{round(dist_per_day/2.5 + day_gain/300)}-{round(dist_per_day/2 + day_gain/200)}小时",
            }

            # Add notes/risks
            risks_list = []
            if is_first and max_ele > 3000:
                risks_list.append("首日注意适应海拔")
            if is_last:
                risks_list.append("最后一天注意体力分配")
            if day_ele > 4000:
                risks_list.append("高海拔区域注意高反")
            if notes:
                risks_list.append(notes[:60])
            entry["risks"] = "；".join(risks_list[:3])

            # Highlights
            if is_first:
                entry["highlights"] = f"开始{route_name}之旅"
            elif is_last:
                entry["highlights"] = f"完成{route_name}全程！"
            else:
                entry["highlights"] = f"{route_name}第{day+1}天精华路段"

            if exp == "新手":
                entry["notes"] = "新手注意控制节奏，每1小时休息5-10分钟"

            if day_ele > 3500:
                entry["notes"] = (entry.get("notes", "") + " 高海拔缓慢行进，多喝水").strip()

            entry["key_points"] = [entry["highlights"]]
            schedule.append(entry)

        return schedule

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        return """📝 [Synthesizer] 开始融合所有 Agent 输出...

正在汇总:
  📊 路线分析结果 → 路线概览
  🎒 装备方案 + 审核结果 → 装备清单
  🛡️ 安全评估结果 → 安全提示
  📅 生成日程安排
  ✅ 生成行前检查清单

📄 正在生成最终方案文档..."""
