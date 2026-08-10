from pydantic import BaseModel
from datetime import datetime


class TripCreate(BaseModel):
    plan_id: int | None = None
    route_id: int | None = None
    title: str
    description: str = ""
    start_date: str | None = None
    end_date: str | None = None
    actual_distance: float | None = None
    actual_elevation_gain: float | None = None
    rating: int = 0
    notes: str = ""
    weather: str = ""


class TripMediaResponse(BaseModel):
    id: int
    trip_id: int
    file_type: str
    file_path: str
    thumbnail_path: str | None = None
    description: str
    taken_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TripResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int | None = None
    route_id: int | None = None
    title: str
    description: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    actual_distance: float | None = None
    actual_elevation_gain: float | None = None
    rating: int
    notes: str
    weather: str
    media: list[TripMediaResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
