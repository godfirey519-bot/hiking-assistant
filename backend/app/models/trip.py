from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class TripRecord(Base):
    __tablename__ = "trip_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_distance: Mapped[float] = mapped_column(Float, nullable=True)  # 实际距离(米)
    actual_elevation_gain: Mapped[float] = mapped_column(Float, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=0)  # 1-5
    notes: Mapped[str] = mapped_column(Text, default="")
    weather: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="trips")
    plan = relationship("Plan", back_populates="trips")
    route = relationship("Route", back_populates="trips")
    media = relationship("TripMedia", back_populates="trip", cascade="all, delete-orphan")
    gear_used = relationship("TripGear", back_populates="trip", cascade="all, delete-orphan")


class TripMedia(Base):
    __tablename__ = "trip_media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_records.id"), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # image / video
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trip = relationship("TripRecord", back_populates="media")


class TripGear(Base):
    __tablename__ = "trip_gear"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_records.id"), nullable=False)
    gear_item_id: Mapped[int] = mapped_column(ForeignKey("gear_items.id"), nullable=False)
    used: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(String(500), default="")

    trip = relationship("TripRecord", back_populates="gear_used")
