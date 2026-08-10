from pydantic import BaseModel
from datetime import datetime


class PlanCreate(BaseModel):
    route_id: int | None = None
    title: str
    description: str = ""
    start_date: str | None = None
    end_date: str | None = None
    participants: int = 1


class PlanSectionResponse(BaseModel):
    id: int
    plan_id: int
    type: str
    title: str
    content: str
    agent_name: str
    reviewed_by: str | None = None
    review_result: str | None = None
    review_notes: str | None = None

    model_config = {"from_attributes": True}


class AgentLogResponse(BaseModel):
    id: int
    plan_id: int
    agent_name: str
    role: str
    status: str
    input: str
    output: str
    thinking: str
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: int
    user_id: int
    route_id: int | None = None
    title: str
    description: str
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    participants: int
    created_at: datetime
    sections: list[PlanSectionResponse] = []
    agent_logs: list[AgentLogResponse] = []

    model_config = {"from_attributes": True}
