from pydantic import BaseModel
from datetime import datetime


class WaypointSchema(BaseModel):
    lat: float
    lng: float
    ele: float | None = None
    time: str | None = None
    name: str | None = None


class RouteCreate(BaseModel):
    name: str
    description: str = ""
    start_point: str = ""
    end_point: str = ""
    duration_days: int = 1
    difficulty: str = "moderate"


class RouteResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    distance: float
    elevation_gain: float
    elevation_loss: float
    max_elevation: float
    min_elevation: float
    difficulty: str
    duration_days: int
    gpx_file_path: str | None = None
    start_point: str
    end_point: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RouteDetailResponse(RouteResponse):
    waypoints: list[WaypointSchema] = []


class GPXUploadResponse(BaseModel):
    success: bool
    route: RouteDetailResponse
    waypoint_count: int
