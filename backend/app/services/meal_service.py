"""徒步路餐推荐服务 — 知识库 + 预算分层 + 路线匹配

基于互联网徒步攻略（抖音/小红书/8264/两步路）的常见路餐推荐，
按预算分为经济型/标准型/高端型三档，支持按路线天数生成每日三餐+路餐计划。
"""
import logging

logger = logging.getLogger(__name__)

# ===== 路餐食材知识库 =====
# 格式: { "name": "品名", "brands": [品牌], "price_range": "区间", "calories": 千卡,
#         "type": "主食/零食/饮品/补剂", "notes": "说明" }

MEAL_DATABASE = {
    # ===== 早餐 =====
    "即食燕麦片": {
        "brands": ["桂格", "西麦", "山姆Member's Mark", "鲍勃红磨坊"],
        "price_range": "15-60元/袋", "calories": 380, "weight_g": 100,
        "type": "早餐主食",
        "budget": "经济",
        "notes": "开水冲泡即食，加坚果果干更佳",
    },
    "冻干粥": {
        "brands": ["海福盛", "苏伯", "和厨"],
        "price_range": "4-8元/杯", "calories": 350, "weight_g": 50,
        "type": "早餐主食",
        "budget": "经济",
        "notes": "5分钟开水冲泡，口味多",
    },
    "山屋早餐": {
        "brands": ["Mountain House", "Backpacker's Pantry"],
        "price_range": "35-60元/袋", "calories": 450, "weight_g": 80,
        "type": "早餐主食",
        "budget": "高端",
        "notes": "进口冻干早餐，美式炒蛋/培根口味",
    },
    "黑芝麻糊": {
        "brands": ["南方黑芝麻", "五谷磨房", "老金磨方"],
        "price_range": "2-5元/包", "calories": 320, "weight_g": 40,
        "type": "早餐主食",
        "budget": "经济",
        "notes": "暖胃早餐，冬季推荐",
    },

    # ===== 路餐/午餐 =====
    "压缩饼干": {
        "brands": ["冠生园", "900压缩干粮", "海军压缩饼干"],
        "price_range": "3-8元/块", "calories": 450, "weight_g": 100,
        "type": "路餐主食",
        "budget": "经济",
        "notes": "高热量耐储存，口感偏干需配水",
    },
    "山之厨冻干饭": {
        "brands": ["山之厨", " Mountain House"],
        "price_range": "25-50元/袋", "calories": 500, "weight_g": 120,
        "type": "路餐主食",
        "budget": "标准",
        "notes": "国货之光，咖喱牛肉/香菇鸡肉口味好",
    },
    "自热米饭": {
        "brands": ["自嗨锅", "莫小仙", "海底捞", "开小灶"],
        "price_range": "15-35元/盒", "calories": 550, "weight_g": 350,
        "type": "路餐主食",
        "budget": "标准",
        "notes": "重但有热饭吃，短线可用，长线不推荐（太重）",
    },
    "方便面/杯面": {
        "brands": ["康师傅", "统一", "出前一丁", "日清合味道"],
        "price_range": "3-10元/杯", "calories": 380, "weight_g": 80,
        "type": "路餐主食",
        "budget": "经济",
        "notes": "最经济的徒步晚餐，加个卤蛋火腿肠升级",
    },
    "山之鲜冻干饭": {
        "brands": ["山之鲜", "Summit To Eat", "Real Turmat"],
        "price_range": "40-80元/袋", "calories": 550, "weight_g": 100,
        "type": "路餐主食",
        "budget": "高端",
        "notes": "高端冻干餐，挪威Real Turmat口味最佳",
    },

    # ===== 蛋白质 =====
    "牛肉干": {
        "brands": ["科尔沁", "牛头牌", "张飞牛肉", "棒棒娃"],
        "price_range": "15-40元/100g", "calories": 300, "weight_g": 100,
        "type": "蛋白质",
        "budget": "标准",
        "notes": "风干牛肉最耐放，麻辣口味开胃",
    },
    "卤蛋/咸鸭蛋": {
        "brands": ["无穷", "乡巴佬", "无穷盐焗蛋"],
        "price_range": "1.5-3元/个", "calories": 80, "weight_g": 50,
        "type": "蛋白质",
        "budget": "经济",
        "notes": "最便宜的蛋白质来源，一天2-3个",
    },
    "午餐肉/火腿肠": {
        "brands": ["SPAM世棒", "梅林", "双汇", "雨润"],
        "price_range": "5-25元/罐", "calories": 250, "weight_g": 100,
        "type": "蛋白质",
        "budget": "经济",
        "notes": "SPAM最香，梅林性价比最高",
    },
    "蛋白棒": {
        "brands": ["ffit8", "PhD", "MyProtein", "Quest"],
        "price_range": "8-20元/支", "calories": 200, "weight_g": 40,
        "type": "蛋白质",
        "budget": "标准",
        "notes": "轻量高蛋白，巧克力口味最受欢迎",
    },
    "即食鸡胸肉": {
        "brands": ["优形", "鲨鱼菲特", "泰森", "肌肉小王子"],
        "price_range": "5-12元/袋", "calories": 130, "weight_g": 100,
        "type": "蛋白质",
        "budget": "标准",
        "notes": "开袋即食，低脂高蛋白",
    },
    "三文鱼/金枪鱼罐头": {
        "brands": ["John West", "雄鸡标", "Calvo"],
        "price_range": "12-25元/罐", "calories": 180, "weight_g": 80,
        "type": "蛋白质",
        "budget": "高端",
        "notes": "Omega-3丰富，配饼干好吃",
    },

    # ===== 碳水/能量 =====
    "能量胶": {
        "brands": ["GU", "SIS", "High5", "康比特"],
        "price_range": "6-15元/支", "calories": 100, "weight_g": 32,
        "type": "能量补充",
        "budget": "标准",
        "notes": "快速补能，爬升前10分钟吃",
    },
    "士力架/巧克力": {
        "brands": ["士力架", "德芙", "费列罗", "瑞士莲"],
        "price_range": "3-10元/条", "calories": 250, "weight_g": 50,
        "type": "能量补充",
        "budget": "经济",
        "notes": "冬季推荐，夏天会化",
    },
    "坚果混合": {
        "brands": ["沃隆", "三只松鼠", "良品铺子", "每日坚果"],
        "price_range": "3-6元/包", "calories": 160, "weight_g": 25,
        "type": "能量补充",
        "budget": "标准",
        "notes": "小包装每日坚果最方便",
    },
    "葡萄糖": {
        "brands": ["康维他葡萄糖", "药房葡萄糖冲剂"],
        "price_range": "10-20元/盒", "calories": 80, "weight_g": 15,
        "type": "能量补充",
        "budget": "经济",
        "notes": "高反时快速补糖，冲水喝",
    },

    # ===== 饮品 =====
    "速溶咖啡": {
        "brands": ["三顿半", "永璞", "雀巢金牌", "UCC", "星巴克Via"],
        "price_range": "2-8元/颗", "calories": 5, "weight_g": 3,
        "type": "饮品",
        "budget": "标准",
        "notes": "三顿半最轻便，星巴克Via口味最接近现磨",
    },
    "电解质粉": {
        "brands": ["宝矿力", "Nuun", "SIS", "GU Hydration"],
        "price_range": "2-6元/条", "calories": 20, "weight_g": 10,
        "type": "饮品",
        "budget": "标准",
        "notes": "防止抽筋脱水，每天2-3条",
    },
    "茶包": {
        "brands": ["立顿", "川宁", "茶颜悦色", "小罐茶"],
        "price_range": "0.5-5元/包", "calories": 0, "weight_g": 2,
        "type": "饮品",
        "budget": "经济",
        "notes": "路上泡茶很有幸福感",
    },
    "奶粉/豆浆粉": {
        "brands": ["德运", "安佳", "龙王", "冰泉"],
        "price_range": "1-3元/条", "calories": 100, "weight_g": 25,
        "type": "饮品",
        "budget": "经济",
        "notes": "早餐配燕麦片，补充蛋白质和钙",
    },
    "维C泡腾片": {
        "brands": ["力度伸", "Airborne", "Berocca"],
        "price_range": "2-5元/片", "calories": 10, "weight_g": 4,
        "type": "饮品",
        "budget": "标准",
        "notes": "预防感冒，改善水质口感",
    },

    # ===== 零食/其他 =====
    "能量棒": {
        "brands": ["Clif Bar", "Kind Bar", "康比特", "Nature Valley"],
        "price_range": "8-20元/支", "calories": 250, "weight_g": 68,
        "type": "零食",
        "budget": "标准",
        "notes": "Clif Bar口味最多，Nature Valley最脆",
    },
    "果干": {
        "brands": ["百草味", "良品铺子", "三只松鼠"],
        "price_range": "5-10元/袋", "calories": 120, "weight_g": 30,
        "type": "零食",
        "budget": "经济",
        "notes": "蔓越莓干/葡萄干/杏干，补充微量元素",
    },
    "即食紫菜汤": {
        "brands": ["苏伯", "海牌", "必品阁"],
        "price_range": "1-3元/包", "calories": 25, "weight_g": 5,
        "type": "零食",
        "budget": "经济",
        "notes": "热水冲泡，轻量暖身，强烈推荐",
    },
}


def recommend_meals(days: int, budget: str = "标准", route_elevation: int = 0,
                    season: str = "春秋季", profile: dict | None = None) -> dict:
    """
    根据徒步天数、预算、路线特征生成每日路餐推荐。

    Args:
        days: 徒步天数
        budget: "经济" / "标准" / "高端"
        route_elevation: 最高海拔
        season: 季节
        profile: 用户画像

    Returns:
        {
            "budget_tier": "标准",
            "estimated_cost_range": "每天约45-80元",
            "daily": [
                {
                    "day": 1,
                    "breakfast": [...],
                    "lunch": [...],
                    "dinner": [...],
                    "snacks": [...],
                    "hydration": "...",
                    "total_calories": 2800,
                }
            ],
            "shopping_list": {...},
            "route_notes": [...],
        }
    """
    budget_filter = {"经济": "经济", "标准": ["经济", "标准"], "高端": ["经济", "标准", "高端"]}

    def filter_by_budget(b):
        allowed = budget_filter.get(budget, ["经济", "标准"])
        return b in allowed if isinstance(allowed, list) else b == allowed

    # 给每个 item 加上 name 字段
    def items():
        return [{"name": k, **v} for k, v in MEAL_DATABASE.items()]

    # 按类型分类
    breakfast_items = [x for x in items() if x["type"] == "早餐主食" and filter_by_budget(x["budget"])]
    lunch_items = [x for x in items() if x["type"] == "路餐主食" and filter_by_budget(x["budget"])]
    protein_items = [x for x in items() if x["type"] == "蛋白质" and filter_by_budget(x["budget"])]
    energy_items = [x for x in items() if x["type"] == "能量补充" and filter_by_budget(x["budget"])]
    drink_items = [x for x in items() if x["type"] == "饮品" and filter_by_budget(x["budget"])]
    snack_items = [x for x in items() if x["type"] == "零食" and filter_by_budget(x["budget"])]

    daily_plans = []
    for day in range(days):
        # 根据天数调整推荐
        is_last = day == days - 1
        is_first = day == 0

        # 选品逻辑：每天轮换不同品牌
        b_idx = day % len(breakfast_items) if breakfast_items else 0
        l_idx = day % len(lunch_items) if lunch_items else 0
        p_idx = day % len(protein_items) if protein_items else 0
        e_idx = day % len(energy_items) if energy_items else 0
        d_idx = day % len(drink_items) if drink_items else 0

        day_plan = {
            "day": day + 1,
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snacks": [],
            "hydration": f"每天至少{2 if route_elevation < 3000 else 3}升水，{'' if season != '夏季' else '夏季加量到4升，'}电解质粉每天2条补充盐分",
        }

        # 早餐：主食 + 饮品
        if breakfast_items:
            bi = breakfast_items[b_idx]
            day_plan["breakfast"].append({
                "name": bi["name"], "brand": bi["brands"][0], "quantity": 1,
                "calories": bi["calories"], "price_est": bi["price_range"],
                "notes": bi["notes"],
            })
        if drink_items:
            di = drink_items[d_idx]
            day_plan["breakfast"].append({
                "name": di["name"], "brand": di["brands"][0], "quantity": 1,
                "calories": di["calories"], "price_est": di["price_range"],
                "notes": "配早餐",
            })

        # 午餐（路餐）：主食 + 蛋白质 + 能量
        if lunch_items:
            li = lunch_items[l_idx]
            day_plan["lunch"].append({
                "name": li["name"], "brand": li["brands"][0], "quantity": 1,
                "calories": li["calories"], "price_est": li["price_range"],
                "notes": li["notes"],
            })
        if protein_items:
            pi = protein_items[p_idx]
            day_plan["lunch"].append({
                "name": pi["name"], "brand": pi["brands"][0], "quantity": 1 + (1 if days > 2 else 0),
                "calories": pi["calories"], "price_est": pi["price_range"],
                "notes": pi["notes"],
            })
        if energy_items:
            ei = energy_items[e_idx]
            day_plan["lunch"].append({
                "name": ei["name"], "brand": ei["brands"][0], "quantity": 2,
                "calories": ei["calories"] * 2, "price_est": ei["price_range"],
                "notes": ei["notes"] + "，上午1支下午1支",
            })

        # 晚餐：主食 + 蛋白质 + 汤 + 饮品
        if lunch_items:
            li2 = lunch_items[(l_idx + 1) % len(lunch_items)] if len(lunch_items) > 1 else lunch_items[l_idx]
            day_plan["dinner"].append({
                "name": li2["name"], "brand": li2["brands"][0], "quantity": 1,
                "calories": li2["calories"], "price_est": li2["price_range"],
                "notes": li2["notes"],
            })
        if protein_items:
            pi2 = protein_items[(p_idx + 1) % len(protein_items)] if len(protein_items) > 1 else protein_items[p_idx]
            day_plan["dinner"].append({
                "name": pi2["name"], "brand": pi2["brands"][0], "quantity": 1,
                "calories": pi2["calories"], "price_est": pi2["price_range"],
                "notes": pi2["notes"],
            })
        # 热汤
        day_plan["dinner"].append({
            "name": "即食紫菜汤", "brand": "苏伯", "quantity": 1,
            "calories": 25, "price_est": "1-3元/包",
            "notes": "热水冲泡，轻量暖身",
        })
        if drink_items and len(drink_items) > 1:
            di2 = drink_items[(d_idx + 1) % len(drink_items)]
            day_plan["dinner"].append({
                "name": di2["name"], "brand": di2["brands"][0], "quantity": 1,
                "calories": di2["calories"], "price_est": di2["price_range"],
                "notes": "晚餐享用",
            })

        # 零食
        if snack_items:
            si = snack_items[day % len(snack_items)]
            day_plan["snacks"].append({
                "name": si["name"], "brand": si["brands"][0], "quantity": 2,
                "calories": si["calories"] * 2, "price_est": si["price_range"],
                "notes": "行进间随时补充",
            })
        day_plan["snacks"].append({
            "name": "坚果混合", "brand": "沃隆/三只松鼠", "quantity": 2,
            "calories": 320, "price_est": "3-6元/包",
            "notes": "每日坚果小包装最方便",
        })

        # 总热量估算
        total_cal = sum(
            item.get("calories", 0) * item.get("quantity", 1)
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]
            for item in day_plan.get(meal_type, [])
        )
        day_plan["total_calories"] = total_cal

        daily_plans.append(day_plan)

    # 购物清单汇总
    shopping = {}
    for day in daily_plans:
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            for item in day.get(meal_type, []):
                key = item["name"]
                if key not in shopping:
                    shopping[key] = {"brand": item["brand"], "quantity": 0, "price_est": item["price_est"]}
                shopping[key]["quantity"] += item["quantity"]

    # 路线相关建议
    route_notes = []
    if route_elevation > 4000:
        route_notes.append("🏔️ 高海拔(>4000m)：食欲下降，带开胃食品（麻辣牛肉干/酸辣粉/榨菜）")
        route_notes.append("🏔️ 高海拔：碳水需求增加50%，每天多带1份主食")
        route_notes.append("🏔️ 高海拔：多喝热水！保温杯+葡萄糖粉缓解高反")
    elif route_elevation > 3000:
        route_notes.append("⛰️ 中等海拔(3000-4000m)：保持正常饮食，注意补水")
    if season == "冬季" or route_elevation > 4000:
        route_notes.append("❄️ 寒冷环境：每日热量需增加20-30%，多带高脂食物（坚果/巧克力/午餐肉）")
        route_notes.append("❄️ 寒冷环境：保温杯必备，热饮提升幸福感和安全性")
    if season == "夏季":
        route_notes.append("☀️ 夏季：水量加倍！每天至少3-4升，电解质每天3条防中暑")
        route_notes.append("☀️ 夏季：巧克力/能量棒可能融化，改带能量胶/坚果/牛肉干")
    if days > 3:
        route_notes.append(f"📦 {days}天长线：建议前2天吃新鲜食物（自热米饭/面包），后期吃冻干/压缩食品减重")
        route_notes.append("📦 长线：第3天起食欲下降，带辣味/酸味开胃食品很重要")
    route_notes.append("💡 小红书攻略：带小包装调味料（辣椒面/盐/酱油）极大提升口味！")
    route_notes.append("💡 抖音徒步博主推荐：紫菜蛋花汤包是轻量化神器")

    # 预算估算
    budget_estimates = {
        "经济": f"每天约{25 + days * 5}~{40 + days * 10}元",
        "标准": f"每天约{45 + days * 5}~{80 + days * 10}元",
        "高端": f"每天约{80 + days * 5}~{150 + days * 10}元",
    }

    return {
        "budget_tier": budget,
        "estimated_cost_range": budget_estimates.get(budget, budget_estimates["标准"]),
        "days": days,
        "daily": daily_plans,
        "shopping_list": shopping,
        "route_notes": route_notes,
    }
