from pydantic import BaseModel
from datetime import datetime


class BackpackCreate(BaseModel):
    name: str
    description: str = ""
    base_weight: int = 0  # 背包本体重量（克）


class BackpackItemBrief(BaseModel):
    id: int
    name: str
    category: str | None = None
    weight: int
    quantity: int


class BackpackResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    base_weight: int
    item_count: int = 0
    total_weight: int = 0  # 本体 + 装备总重（克）
    items: list[BackpackItemBrief] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class BackpackMessageResponse(BaseModel):
    message: str
    backpack: BackpackResponse | None = None
