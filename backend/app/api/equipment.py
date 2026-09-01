from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.gear import GearCategory, GearItem
from app.schemas.gear import (
    GearCategoryCreate, GearCategoryResponse,
    GearItemCreate, GearItemResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/equipment", tags=["装备"])


# ========== 装备分类 ==========

@router.get("/categories", response_model=list[GearCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GearCategory).order_by(GearCategory.sort_order)
    )
    return result.scalars().all()


@router.post("/categories", response_model=GearCategoryResponse)
async def create_category(
    data: GearCategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = GearCategory(**data.model_dump())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


# ========== 装备管理 ==========

@router.get("/items", response_model=list[GearItemResponse])
async def list_items(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category_id: int | None = None,
):
    from sqlalchemy.orm import selectinload
    query = select(GearItem).options(selectinload(GearItem.category)).where(GearItem.user_id == user.id)
    if category_id:
        query = query.where(GearItem.category_id == category_id)
    result = await db.execute(query.order_by(GearItem.created_at.desc()))
    return result.scalars().all()


@router.post("/items", response_model=GearItemResponse)
async def create_item(
    data: GearItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 校验分类存在（避免 FK 约束错误 500）
    cat_result = await db.execute(select(GearCategory).where(GearCategory.id == data.category_id))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(400, "装备分类不存在")

    item = GearItem(user_id=user.id, **data.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)

    # eager load category（异步会话下懒加载会触发 MissingGreenlet）
    item.category = category

    return item


@router.put("/items/{item_id}", response_model=GearItemResponse)
async def update_item(
    item_id: int,
    data: GearItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GearItem).where(GearItem.id == item_id, GearItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "装备不存在")

    # 校验新分类存在
    cat_result = await db.execute(select(GearCategory).where(GearCategory.id == data.category_id))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(400, "装备分类不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await db.flush()
    await db.refresh(item)

    # eager load category
    item.category = category

    return item


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GearItem).where(GearItem.id == item_id, GearItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "装备不存在")
    await db.delete(item)
    return {"success": True}


# ========== 初始化默认分类 ==========

DEFAULT_CATEGORIES = [
    ("背负系统", "backpack", 1),
    ("睡眠系统", "tent", 2),
    ("饮食系统", "cooking-pot", 3),
    ("服装-上衣", "shirt", 4),
    ("服装-下装", "pants", 5),
    ("鞋袜", "footprints", 6),
    ("登山杖/冰爪", "trekking-pole", 7),
    ("照明", "flashlight", 8),
    ("电子设备", "smartphone", 9),
    ("急救/药品", "heart-pulse", 10),
    ("导航通讯", "map", 11),
    ("工具", "wrench", 12),
    ("其他", "package", 99),
]


@router.post("/init-defaults")
async def init_default_categories(
    db: AsyncSession = Depends(get_db),
):
    """初始化默认装备分类（首次使用）"""
    existing = await db.execute(select(GearCategory))
    if existing.scalars().first():
        return {"message": "分类已存在"}

    for name, icon, sort_order in DEFAULT_CATEGORIES:
        cat = GearCategory(name=name, icon=icon, sort_order=sort_order)
        db.add(cat)
    return {"message": f"已创建 {len(DEFAULT_CATEGORIES)} 个默认分类"}
