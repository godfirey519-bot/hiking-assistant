from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft → planning → reviewing → completed / failed
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    participants: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="plans")
    route = relationship("Route", back_populates="plans")
    sections = relationship("PlanSection", back_populates="plan", cascade="all, delete-orphan")
    agent_logs = relationship("PlanAgentLog", back_populates="plan", cascade="all, delete-orphan")
    trips = relationship("TripRecord", back_populates="plan")
    shares = relationship("PlanShare", back_populates="plan", cascade="all, delete-orphan")


class PlanSection(Base):
    __tablename__ = "plan_sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    # equipment / route / budget / commute / safety / schedule
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(50), nullable=True)
    review_result: Mapped[str] = mapped_column(String(20), nullable=True)
    # approved / rejected / needs_modification
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("Plan", back_populates="sections")


class PlanAgentLog(Base):
    __tablename__ = "plan_agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # planner / reviewer / orchestrator / synthesizer
    status: Mapped[str] = mapped_column(String(20), default="running")
    # running / completed / failed
    input: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[str] = mapped_column(Text, default="")
    thinking: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    plan = relationship("Plan", back_populates="agent_logs")


class PlanShare(Base):
    """方案分享链接（免登录只读访问）"""

    __tablename__ = "plan_shares"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("Plan", back_populates="shares")
