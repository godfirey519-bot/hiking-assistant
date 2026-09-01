"""路餐服务测试：预算分层/天数/海拔/季节"""
from app.services.meal_service import recommend_meals


def test_meals_basic_structure():
    result = recommend_meals(days=3, budget="标准")
    assert result["budget_tier"] == "标准"
    assert len(result["daily"]) == 3
    day1 = result["daily"][0]
    assert day1["day"] == 1
    assert day1["breakfast"], "早餐不能为空"
    assert day1["lunch"], "午餐不能为空"
    assert day1["dinner"], "晚餐不能为空"
    assert day1["snacks"], "零食不能为空"
    assert day1["total_calories"] > 0
    # 每餐都带品牌/热量/价格
    for meal in day1["breakfast"] + day1["lunch"] + day1["dinner"]:
        assert meal["name"]
        assert meal["brand"]
        assert meal["calories"] > 0
        assert meal["price_est"]


def test_meals_budget_tier_filter():
    eco = recommend_meals(days=2, budget="经济")
    for day in eco["daily"]:
        for meal in day["breakfast"] + day["lunch"] + day["dinner"]:
            # 经济档不应出现高端商品（山屋早餐等 budget=高端）
            assert "山屋" not in meal["name"]
            assert "Real Turmat" not in meal["name"]

    lux = recommend_meals(days=2, budget="高端")
    # 高端档应包含各档位商品（允许高端商品出现）
    all_names = [m["name"] for day in lux["daily"] for meal in
                 (day["breakfast"], day["lunch"], day["dinner"]) for m in meal]
    assert all_names, "高端档应产出餐食"


def test_meals_days_and_hydration():
    d1 = recommend_meals(days=1, budget="标准")
    assert len(d1["daily"]) == 1

    # 高海拔 → 3 升水提示
    high = recommend_meals(days=1, budget="标准", route_elevation=3500)
    assert "3升" in high["daily"][0]["hydration"]

    # 低海拔 → 2 升水提示
    low = recommend_meals(days=1, budget="标准", route_elevation=1000)
    assert "2升" in low["daily"][0]["hydration"]

    # 夏季 → 4 升提示
    summer = recommend_meals(days=1, budget="标准", season="夏季")
    assert "4升" in summer["daily"][0]["hydration"]


def test_meals_shopping_list_and_notes():
    result = recommend_meals(days=2, budget="经济")
    assert isinstance(result["shopping_list"], dict)
    assert result["shopping_list"], "购物清单不能为空"
    assert isinstance(result["route_notes"], list)
