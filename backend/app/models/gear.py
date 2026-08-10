from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from datetime import datetime


class GearCategory(Base):
    __tablename__ = "gear_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="package")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    items = relationship("GearItem", back_populates="category")


class GearItem(Base):
    __tablename__ = "gear_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("gear_categories.id"), nullable=False)
    backpack_id: Mapped[int] = mapped_column(ForeignKey("backpacks.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    weight: Mapped[int] = mapped_column(Integer, default=0)  # 克
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="gear_items")
    category = relationship("GearCategory", back_populates="items")
    backpack = relationship("Backpack", back_populates="gear_items")
