"""🎒 装备规划 Agent — 基于路线/季节/个人情况推荐装备清单"""
from app.agents.base import BaseAgent, AgentResult
import json
import logging

logger = logging.getLogger(__name__)

# 装备推荐知识库 — 按徒步类型和季节分类
EQUIPMENT_RECOMMENDATIONS = {
    "睡眠系统": {
        "必备": [
            {"name": "帐篷", "brand_suggestions": ["三峰出", "Naturehike", "MSR", "Big Agnes"], "weight_range": "500-2500g", "notes": "根据季节选择三季帐或四季帐"},
            {"name": "睡袋", "brand_suggestions": ["黑冰", "天石", "Sea to Summit", "Western Mountaineering"], "weight_range": "400-1500g", "notes": "温标应比预期最低温低5-10°C"},
            {"name": "防潮垫", "brand_suggestions": ["Therm-a-Rest", "Sea to Summit", "Naturehike"], "weight_range": "300-800g", "notes": "R值根据季节选择"},
        ],
    },
    "炊具系统": {
        "必备": [
            {"name": "炉头", "brand_suggestions": ["Soto", "MSR", "火枫", "BRS"], "weight_range": "25-200g", "notes": "分体炉头比一体式更稳"},
            {"name": "气罐", "brand_suggestions": ["火枫", "脉鲜", "MSR"], "weight_range": "230-450g", "notes": "2-3天行程带1个230g罐"},
            {"name": "锅具", "brand_suggestions": ["Keith", "Snow Peak", "TOAKS"], "weight_range": "100-300g", "notes": "钛锅轻便，铝锅便宜"},
            {"name": "餐具", "brand_suggestions": ["Sea to Summit", "GSI"], "weight_range": "10-50g", "notes": "折叠筷+勺即可"},
        ],
        "建议": [],
    },
    "服装-上衣": {
        "必备": [
            {"name": "速干T恤", "brand_suggestions": ["Patagonia", "Arc'teryx", "Decathlon"], "quantity": 2, "notes": "美利奴羊毛最佳，防臭"},
            {"name": "抓绒衣/棉服", "brand_suggestions": ["Patagonia", "Mountain Hardwear", "凯乐石"], "weight_range": "200-500g", "notes": "静态保暖层"},
            {"name": "冲锋衣", "brand_suggestions": ["Arc'teryx", "Mammut", "凯乐石", "探路者"], "weight_range": "300-600g", "notes": "Gore-Tex或类似防水透气膜"},
        ],
        "按季节": {
            "冬季": [{"name": "羽绒服", "brand_suggestions": ["Rab", "Mountain Hardwear", "黑冰"], "weight_range": "300-600g"}],
            "高海拔": [{"name": "羽绒服", "brand_suggestions": ["Rab", "Mountain Hardwear", "黑冰"], "weight_range": "300-600g"}],
        },
    },
    "服装-下装": {
        "必备": [
            {"name": "速干裤", "brand_suggestions": ["Patagonia", "Arc'teryx", "凯乐石"], "quantity": 1, "notes": "可拆卸裤腿的更灵活"},
            {"name": "冲锋裤", "brand_suggestions": ["Arc'teryx", "Mammut", "凯乐石"], "weight_range": "250-500g", "notes": "雨天/大风时穿着"},
        ],
    },
    "鞋袜": {
        "必备": [
            {"name": "徒步鞋/登山鞋", "brand_suggestions": ["Salomon", "Merrell", "Scarpa", "凯乐石"], "notes": "中帮防水款最通用"},
            {"name": "徒步袜", "brand_suggestions": ["Smartwool", "Darn Tough", "Injinji"], "quantity": 2, "notes": "美利奴羊毛，带1双备用"},
        ],
        "建议": [
            {"name": "营地鞋/溯溪鞋", "notes": "轻便拖鞋，营地休息用"},
            {"name": "雪套", "notes": "雨/雪/泥地需要"},
        ],
    },
    "照明": {
        "必备": [
            {"name": "头灯", "brand_suggestions": ["Petzl", "Black Diamond", "Nitecore"], "weight_range": "30-100g", "notes": "带备用电池"},
        ],
    },
    "急救": {
        "必备": [
            {"name": "急救包", "contents": ["创可贴", "碘伏棉签", "弹性绷带", "止痛药", "防高反药", "肠胃药", "防蚊虫"], "notes": "根据路线调整药品"},
            {"name": "救生毯", "weight_range": "50-100g", "notes": "应急保温"},
        ],
    },
    "导航通讯": {
        "必备": [
            {"name": "手机+离线地图", "notes": "下载两步路/奥维离线地图"},
            {"name": "充电宝", "quantity": 1, "capacity": "10000-20000mAh", "notes": "2天以上建议20000mAh"},
        ],
        "建议": [
            {"name": "卫星通讯设备", "notes": "无信号区域建议携带，如inReach Mini"},
            {"name": "对讲机", "notes": "多人队伍建议"},
        ],
    },
    "饮水": {
        "必备": [
            {"name": "水袋/水瓶", "capacity": "2-3L", "notes": "根据水源间隔调整"},
            {"name": "净水器/净水片", "brand_suggestions": ["Sawyer", "Katadyn", "SteriPEN"], "notes": "野外取水必备"},
        ],
    },
    "食物": {
        "必备": [
            {"name": "路餐", "notes": "坚果、能量棒、肉干、巧克力，每天约500-700g"},
            {"name": "营地餐", "notes": "冻干食品/泡面/自热米饭，每天约300-500g"},
        ],
    },
    "工具": {
        "必备": [
            {"name": "登山杖", "quantity": 2, "brand_suggestions": ["Black Diamond", "LEKI", "Naturehike"], "notes": "双杖更安全省力"},
            {"name": "多功能刀", "brand_suggestions": ["Victorinox", "Leatherman"], "notes": "至少带一把"},
        ],
        "建议": [
            {"name": "冰爪", "notes": "冰雪路面必备"},
            {"name": "冰镐", "notes": "雪山/冰川需要"},
        ],
    },
}


class EquipmentPlannerAgent(BaseAgent):
    name = "EquipmentPlanner"
    role = "planner"
    description = "装备规划专家 Agent，根据路线难度/季节/天数/个人背包推荐装备清单"

    @property
    def output_schema_hint(self) -> str:
        return """```json
{
  "thinking": "装备规划的分析推理过程",
  "output": {
    "equipment_by_category": {
      "分类名": [
        {"name": "装备名", "priority": "必备", "quantity": 1, "brand_suggestions": [], "notes": "说明"}
      ]
    },
    "total_items": 25,
    "essential_count": 18,
    "suggested_count": 7,
    "conditions": {"difficulty": "中等", "duration_days": 2, "max_elevation": 1918},
    "weight_analysis": {"estimated_total_kg": 12.5, "advice": "重量建议"},
    "principles_applied": ["应用的轻量化原则"]
  }
}
```"""

    @property
    def system_prompt(self) -> str:
        return """你是一位专业徒步装备规划师，擅长轻量化和安全装备推荐。

## 你的原则
1. **安全第一**: 保命装备（急救、照明、导航）不可妥协
2. **轻量化**: 在保证安全的前提下尽量减轻负重（目标 < 体重20%）
3. **因地制宜**: 根据路线、季节、海拔调整装备
4. **物尽其用**: 优先利用用户已有的装备，避免重复购买
5. **分层推荐**: 必备 > 建议 > 可选，每项标注理由

## 装备分类
- 睡眠系统: 帐篷、睡袋、防潮垫
- 炊具系统: 炉头、气罐、锅具、餐具
- 服装: 排汗层、保暖层、防护层（三层穿衣法）
- 鞋袜: 徒步鞋、袜子
- 照明: 头灯、备用电池
- 急救: 急救包、药品
- 导航通讯: 手机/地图、充电宝、卫星设备
- 饮水: 水袋/水瓶、净水设备
- 食物: 路餐、营地餐
- 工具: 登山杖、刀具、冰爪等

## 输出格式
以 JSON 格式输出装备清单，每个装备包含:
- name: 装备名称
- category: 所属分类
- priority: 必备/建议/可选
- quantity: 数量
- weight_estimate_g: 预估重量
- reason: 推荐理由
- alternatives: 替代方案
- search_keywords: 用于在网络平台搜索评测的关键词
"""

    def build_user_message(self, user_input: str, context: dict | None = None) -> str:
        """构建用户消息，附加装备知识库作为参考"""
        base_msg = super().build_user_message(user_input, context)
        # 将装备知识库作为参考信息传递给 LLM
        knowledge_summary = {
            "装备知识库": {
                cat: {"items": [item["name"] for item in items.get("必备", [])]}
                for cat, items in EQUIPMENT_RECOMMENDATIONS.items()
            }
        }
        return base_msg + f"\n\n## 参考知识库\n```json\n{json.dumps(knowledge_summary, ensure_ascii=False, indent=2)}\n```\n\n请基于上述知识库和用户需求，输出结构化的装备推荐方案。知识库中的品牌和规格可作为参考。"

    async def _execute_with_tools(self, user_input: str, context: dict | None = None) -> dict:
        """基于路线和用户情况生成装备推荐"""
        route: dict = (context or {}).get("route_data", {})
        difficulty = route.get("difficulty", "中等")
        duration_days = route.get("duration_days", 2)
        max_ele = route.get("max_elevation_m", 0)
        user_gear = (context or {}).get("user_gear", [])

        # 判断条件
        is_winter = "冬" in user_input or "雪" in user_input
        is_high_altitude = max_ele > 3000
        is_hard = difficulty in ("困难", "较难", "专业级")

        equipment_list = []
        total_weight = 0

        for category, data in EQUIPMENT_RECOMMENDATIONS.items():
            # 必备装备
            for item in data.get("必备", []):
                equipment_list.append({
                    "name": item["name"],
                    "category": category,
                    "priority": "必备",
                    "quantity": item.get("quantity", 1),
                    "brand_suggestions": item.get("brand_suggestions", []),
                    "notes": item.get("notes", ""),
                })

            # 建议装备（困难路线）
            if is_hard or is_high_altitude:
                for item in data.get("建议", []):
                    equipment_list.append({
                        "name": item["name"],
                        "category": category,
                        "priority": "建议",
                        "quantity": item.get("quantity", 1),
                        "notes": item.get("notes", ""),
                    })

            # 按季节/海拔的额外装备
            seasonal = data.get("按季节", {})
            if is_winter and "冬季" in seasonal:
                for item in seasonal["冬季"]:
                    equipment_list.append({
                        "name": item["name"],
                        "category": category,
                        "priority": "必备（冬季）",
                        "quantity": item.get("quantity", 1),
                        "brand_suggestions": item.get("brand_suggestions", []),
                        "notes": item.get("notes", ""),
                    })

            if is_high_altitude and "高海拔" in seasonal:
                for item in seasonal["高海拔"]:
                    equipment_list.append({
                        "name": item["name"],
                        "category": category,
                        "priority": "必备（高海拔）",
                        "quantity": item.get("quantity", 1),
                        "brand_suggestions": item.get("brand_suggestions", []),
                        "notes": item.get("notes", ""),
                    })

        # 按类别分组
        grouped = {}
        for item in equipment_list:
            cat = item["category"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(item)

        return {
            "equipment_by_category": grouped,
            "total_items": len(equipment_list),
            "essential_count": sum(1 for i in equipment_list if "必备" in i["priority"]),
            "suggested_count": sum(1 for i in equipment_list if "建议" in i["priority"]),
            "conditions": {
                "difficulty": difficulty,
                "duration_days": duration_days,
                "max_elevation": max_ele,
                "is_winter": is_winter,
                "is_high_altitude": is_high_altitude,
            },
            "principles_applied": [
                "三层穿衣法（排汗+保暖+防护）",
                "轻量化优先（目标 < 体重20%）",
                "安全装备不可妥协",
                f"基于{difficulty}难度和{duration_days}天行程",
            ],
        }

    def _generate_thinking(self, user_input: str, context: dict | None = None) -> str:
        route = (context or {}).get("route_data", {})
        difficulty = route.get("difficulty", "中等")
        duration = route.get("duration_days", 2)
        max_ele = route.get("max_elevation_m", 0)

        lines = [
            "🎒 [EquipmentPlanner] 开始制定装备方案...",
            "",
            "📊 分析条件:",
            f"  - 路线难度: {difficulty}",
            f"  - 行程天数: {duration} 天",
            f"  - 最高海拔: {max_ele}m" if max_ele else "  - 最高海拔: 未知",
            "",
            "🔍 装备规划思路:",
            "  1. 睡眠系统 → 根据最低温度和海拔选帐篷+睡袋",
            "  2. 服装系统 → 三层穿衣法，根据季节调整",
            "  3. 炊具系统 → 根据天数计算燃料需求",
            "  4. 安全装备 → 急救/照明/导航，不可妥协",
            "  5. 工具 → 登山杖必备，其他按需",
            "",
            "📋 正在搜索各平台装备评测...",
            "  - 8264户外资料网 → 查看国内装备评测",
            "  - REI → 查看国际品牌用户评价",
            "  - 小红书 → 查看真实用户使用体验",
            "  - B站 → 查看装备实测视频",
            "",
            "⚖️ 重量估算（目标 < 体重20%，约12-15kg）...",
        ]

        if difficulty in ("困难", "专业级"):
            lines.extend([
                "",
                "⚠️ 高难度路线额外提醒:",
                "  - 建议携带卫星通讯设备",
                "  - 急救包需升级（增加外伤处理能力）",
                "  - 备用食物至少多带1天量",
            ])

        return "\n".join(lines)
