from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    distance: Mapped[float] = mapped_column(Float, default=0)  # 米
    elevation_gain: Mapped[float] = mapped_column(Float, default=0)  # 累计爬升(米)
    elevation_loss: Mapped[float] = mapped_column(Float, default=0)  # 累计下降(米)
    max_elevation: Mapped[float] = mapped_column(Float, default=0)
    min_elevation: Mapped[float] = mapped_column(Float, default=0)
    difficulty: Mapped[str] = mapped_column(String(20), default="moderate")  # easy/moderate/hard/expert
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    gpx_file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    start_point: Mapped[str] = mapped_column(String(200), default="")
    end_point: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="routes")
    waypoints = relationship("RouteWaypoint", back_populates="route", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="route")
    trips = relationship("TripRecord", back_populates="route")


class RouteWaypoint(Base):
    __tablename__ = "route_waypoints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation: Mapped[float] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=True)
    point_order: Mapped[int] = mapped_column(Integer, default=0)

    route = relationship("Route", back_populates="waypoints")
