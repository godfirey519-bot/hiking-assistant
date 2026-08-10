from pydantic import BaseModel
from datetime import datetime


class GearCategoryCreate(BaseModel):
    name: str
    icon: str = "package"
    sort_order: int = 0


class GearCategoryResponse(BaseModel):
    id: int
    name: str
    icon: str
    sort_order: int

    model_config = {"from_attributes": True}


class GearItemCreate(BaseModel):
    category_id: int
    backpack_id: int | None = None
    name: str
    brand: str = ""
    model: str = ""
    weight: int = 0  # 克
    quantity: int = 1
    description: str = ""


class GearItemResponse(BaseModel):
    id: int
    user_id: int
    category_id: int
    backpack_id: int | None = None
    name: str
    brand: str
    model: str
    weight: int
    quantity: int
    description: str
    image_url: str | None = None
    category: GearCategoryResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
