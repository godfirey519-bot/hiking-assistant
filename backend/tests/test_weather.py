"""天气服务测试：Open-Meteo 解析/恶劣天气标记/出发日切取/mock 外部 API"""
import json

import pytest

from app.services import weather_service


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeAsyncClient:
    """替换 httpx.AsyncClient：记录请求参数并返回预设响应（模拟 forecast_days 截断）"""

    def __init__(self, payload, **kwargs):
        self._payload = payload
        self.captured_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, **kwargs):
        self.captured_params = params
        # 模拟 Open-Meteo：仅返回 forecast_days 天数据
        import copy
        payload = copy.deepcopy(self._payload)
        fd = params.get("forecast_days", len(payload["daily"]["time"]))
        for key in ("time", "temperature_2m_max", "temperature_2m_min",
                    "precipitation_probability_max", "wind_speed_10m_max", "weather_code"):
            payload["daily"][key] = payload["daily"][key][:fd]
        return FakeResponse(payload)


def _make_payload(codes, temps_min=None, temps_max=None):
    n = len(codes)
    return {
        "latitude": 27.99,
        "longitude": 86.93,
        "daily": {
            "time": [f"2026-09-{i+1:02d}" for i in range(n)],
            "temperature_2m_max": temps_max or [20.0] * n,
            "temperature_2m_min": temps_min or [10.0] * n,
            "precipitation_probability_max": [30] * n,
            "wind_speed_10m_max": [15.0] * n,
            "weather_code": codes,
        },
    }


async def test_fetch_weather_parses_and_flags(monkeypatch):
    # code 95 = 雷暴（严重）; code 80 = 阵雨（注意）; code 1 = 晴
    payload = _make_payload([1, 80, 95], temps_min=[10, 8, 4])
    fake = FakeAsyncClient(payload)
    monkeypatch.setattr(weather_service.httpx, "AsyncClient", lambda **kw: fake)

    result = await weather_service.fetch_weather(27.99, 86.93, days=3)
    assert len(result["daily"]) == 3
    assert result["has_severe"] is True
    assert result["has_caution"] is True
    assert result["daily"][0]["weather_desc"] != "未知"
    assert result["summary"]
    # 请求参数正确
    assert fake.captured_params["latitude"] == 27.99
    assert "weather_code" in fake.captured_params["daily"]


async def test_fetch_weather_no_severe(monkeypatch):
    payload = _make_payload([1, 2, 3])
    fake = FakeAsyncClient(payload)
    monkeypatch.setattr(weather_service.httpx, "AsyncClient", lambda **kw: fake)

    result = await weather_service.fetch_weather(27.99, 86.93, days=3)
    assert result["has_severe"] is False
    assert result["has_caution"] is False
    assert result["daily"][0]["is_severe"] is False


async def test_fetch_weather_start_date_cut(monkeypatch):
    """指定出发日期后，只返回徒步期间的预报"""
    from datetime import date, timedelta
    start = (date.today() + timedelta(days=2)).isoformat()
    payload = _make_payload([1, 2, 3, 4, 5])
    fake = FakeAsyncClient(payload)
    monkeypatch.setattr(weather_service.httpx, "AsyncClient", lambda **kw: fake)

    result = await weather_service.fetch_weather(27.99, 86.93, days=2, start_date=start)
    assert len(result["daily"]) == 2  # 切掉前 2 天
    assert result["daily"][0]["date"] == payload["daily"]["time"][2]


async def test_fetch_weather_beyond_16d_window(monkeypatch):
    """出发日期超出免费预报窗口 → 空数据 + 明确提示，不请求 API"""
    from datetime import date, timedelta
    start = (date.today() + timedelta(days=20)).isoformat()
    called = {"flag": False}

    class NeverCalled:
        def __init__(self, **kw):
            called["flag"] = True
    monkeypatch.setattr(weather_service.httpx, "AsyncClient", NeverCalled)

    result = await weather_service.fetch_weather(27.99, 86.93, days=2, start_date=start)
    assert result["daily"] == []
    assert "16天" in result["summary"]
    assert called["flag"] is False


async def test_fetch_weather_api_error_fallback(monkeypatch):
    """API 异常 → 返回带 error 的空结果而非抛出"""

    class FailingClient:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None, **kwargs):
            raise Exception("connection refused")

    monkeypatch.setattr(weather_service.httpx, "AsyncClient", FailingClient)
    result = await weather_service.fetch_weather(27.99, 86.93, days=3)
    assert result["daily"] == []
    assert "error" in result


def test_hiking_weather_advice_no_go():
    weather = {
        "daily": [
            {"date": "09-01", "weather_desc": "雷暴", "is_severe": True, "is_caution": False,
             "temp_min_c": 10, "temp_max_c": 18, "precip_prob": 80, "wind_max_kmh": 20},
        ]
    }
    advice = weather_service.get_hiking_weather_advice(weather)
    assert advice["go_nogo"] == "no_go"
    assert any("恶劣" in r for r in advice["risk_factors"])


def test_hiking_weather_advice_empty():
    advice = weather_service.get_hiking_weather_advice({"daily": []})
    assert advice["go_nogo"] == "conditional_go"
