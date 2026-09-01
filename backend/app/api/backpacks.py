"""背包方案 API — 背包 CRUD + 预设方案 + 装备挂载

背包方案把用户的装备组织成可复用配置（轻装/标准/重装/冬季），
一键创建预设并自动挂载对应装备。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.backpack import Backpack
from app.models.gear import GearCategory, GearItem
from app.schemas.backpack import BackpackCreate, BackpackResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/backpacks", tags=["背包方案"])

# ===== 预设背包方案 =====
# items: [{name, category(分类名), weight_g, quantity}]
BACKPACK_PRESETS = {
    "轻装单日": {
        "description": "当日往返轻量方案，只带必需品",
        "base_weight": 1200,
        "items": [
            {"name": "冲顶包/腰包 (15-25L)", "category": "背负系统", "weight_g": 500, "quantity": 1},
            {"name": "头灯", "category": "照明", "weight_g": 60, "quantity": 1},
            {"name": "急救包", "category": "急救/药品", "weight_g": 300, "quantity": 1},
            {"name": "水袋/水瓶 (2-3L)", "category": "饮食系统", "weight_g": 150, "quantity": 1},
            {"name": "防晒霜 (SPF50+)", "category": "急救/药品", "weight_g": 60, "quantity": 1},
            {"name": "速干T恤 (长袖)", "category": "服装-上衣", "weight_g": 180, "quantity": 1},
        ],
    },
    "标准周末": {
        "description": "2-3 天标准露营方案，含睡眠与炊具系统",
        "base_weight": 2200,
        "items": [
            {"name": "大背包 (50-70L)", "category": "背负系统", "weight_g": 2200, "quantity": 1},
            {"name": "帐篷", "category": "睡眠系统", "weight_g": 2000, "quantity": 1},
            {"name": "睡袋", "category": "睡眠系统", "weight_g": 1200, "quantity": 1},
            {"name": "防潮垫", "category": "睡眠系统", "weight_g": 550, "quantity": 1},
            {"name": "炉头", "category": "饮食系统", "weight_g": 80, "quantity": 1},
            {"name": "气罐", "category": "饮食系统", "weight_g": 350, "quantity": 2},
            {"name": "锅具套装", "category": "饮食系统", "weight_g": 400, "quantity": 1},
            {"name": "头灯", "category": "照明", "weight_g": 60, "quantity": 1},
            {"name": "急救包", "category": "急救/药品", "weight_g": 300, "quantity": 1},
            {"name": "登山杖 (双杖)", "category": "登山杖/冰爪", "weight_g": 250, "quantity": 2},
            {"name": "水袋/水瓶 (2-3L)", "category": "饮食系统", "weight_g": 150, "quantity": 2},
        ],
    },
    "重装长线": {
        "description": "5 天以上长线重装方案，含卫星通讯与备用物资",
        "base_weight": 3200,
        "items": [
            {"name": "大背包 (50-70L)", "category": "背负系统", "weight_g": 2200, "quantity": 1},
            {"name": "帐篷", "category": "睡眠系统", "weight_g": 2000, "quantity": 1},
            {"name": "睡袋", "category": "睡眠系统", "weight_g": 1500, "quantity": 1},
            {"name": "防潮垫", "category": "睡眠系统", "weight_g": 550, "quantity": 1},
            {"name": "羽绒服 (营地用)", "category": "服装-上衣", "weight_g": 450, "quantity": 1},
            {"name": "炉头", "category": "饮食系统", "weight_g": 80, "quantity": 1},
            {"name": "气罐", "category": "饮食系统", "weight_g": 350, "quantity": 3},
            {"name": "锅具套装", "category": "饮食系统", "weight_g": 400, "quantity": 1},
            {"name": "净水器/净水片", "category": "饮食系统", "weight_g": 60, "quantity": 1},
            {"name": "充电宝 (20000mAh+)", "category": "电子设备", "weight_g": 450, "quantity": 2},
            {"name": "卫星电话/SOS设备", "category": "导航通讯", "weight_g": 250, "quantity": 1},
            {"name": "急救包", "category": "急救/药品", "weight_g": 400, "quantity": 1},
            {"name": "登山杖 (双杖)", "category": "登山杖/冰爪", "weight_g": 250, "quantity": 2},
        ],
    },
    "冬季雪山": {
        "description": "冬季/雪山方案，保暖与防滑优先",
        "base_weight": 2800,
        "items": [
            {"name": "大背包 (50-70L)", "category": "背负系统", "weight_g": 2200, "quantity": 1},
            {"name": "羽绒服 (营地用)", "category": "服装-上衣", "weight_g": 600, "quantity": 1},
            {"name": "保暖内衣", "category": "服装-上衣", "weight_g": 250, "quantity": 2},
            {"name": "冲锋裤 (硬壳)", "category": "服装-下装", "weight_g": 450, "quantity": 1},
            {"name": "雪套", "category": "鞋袜", "weight_g": 200, "quantity": 1},
            {"name": "冰爪", "category": "登山杖/冰爪", "weight_g": 700, "quantity": 1},
            {"name": "保温杯", "category": "饮食系统", "weight_g": 350, "quantity": 1},
            {"name": "急救包", "category": "急救/药品", "weight_g": 300, "quantity": 1},
            {"name": "头灯", "category": "照明", "weight_g": 60, "quantity": 1},
            {"name": "备用电池", "category": "照明", "weight_g": 50, "quantity": 4},
            {"name": "气罐", "category": "饮食系统", "weight_g": 350, "quantity": 2},
        ],
    },
}


def _serialize_backpack(bp: Backpack) -> dict:
    """手动序列化（异步会话下避免懒加载 MissingGreenlet）"""
    items = bp.gear_items or []
    item_count = sum(i.quantity or 1 for i in items)
    total_weight = (bp.base_weight or 0) + sum((i.weight or 0) * (i.quantity or 1) for i in items)
    return {
        "id": bp.id,
        "user_id": bp.user_id,
        "name": bp.name,
        "description": bp.description or "",
        "base_weight": bp.base_weight or 0,
        "item_count": item_count,
        "total_weight": total_weight,
        "items": [
            {
                "id": i.id,
                "name": i.name,
                "category": i.category.name if i.category else None,
                "weight": i.weight or 0,
                "quantity": i.quantity or 1,
            }
            for i in items
        ],
        "created_at": bp.created_at,
    }


async def _load_bp(db: AsyncSession, backpack_id: int) -> Backpack:
    """重新查询背包（预加载 gear_items + category）。

    注意：同会话内对象在身份映射中被复用，直接再次 select 不会刷新
    已加载的关系（gear_items 可能仍是旧状态），因此先 expire_all 强制重读。
    """
    db.expire_all()
    result = await db.execute(
        select(Backpack)
        .options(selectinload(Backpack.gear_items).selectinload(GearItem.category))
        .where(Backpack.id == backpack_id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[BackpackResponse])
async def list_backpacks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Backpack)
        .options(selectinload(Backpack.gear_items).selectinload(GearItem.category))
        .where(Backpack.user_id == user.id)
        .order_by(Backpack.created_at.desc())
    )
    return [_serialize_backpack(bp) for bp in result.scalars().all()]


@router.post("/", response_model=BackpackResponse)
async def create_backpack(
    data: BackpackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bp = Backpack(user_id=user.id, name=data.name, description=data.description,
                  base_weight=data.base_weight)
    db.add(bp)
    await db.flush()
    bp = await _load_bp(db, bp.id)
    return _serialize_backpack(bp)


@router.post("/preset/{preset_name}", response_model=BackpackResponse)
async def create_from_preset(
    preset_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按预设创建背包 + 自动创建并挂载对应装备"""
    preset = BACKPACK_PRESETS.get(preset_name)
    if not preset:
        raise HTTPException(404, f"预设方案不存在: {preset_name}（可选: {list(BACKPACK_PRESETS)}）")

    bp = Backpack(user_id=user.id, name=preset_name, description=preset["description"],
                  base_weight=preset["base_weight"])
    db.add(bp)
    await db.flush()

    # 分类名 → id 映射
    cat_result = await db.execute(select(GearCategory))
    cat_id = {c.name: c.id for c in cat_result.scalars().all()}

    created = 0
    for item in preset["items"]:
        cid = cat_id.get(item["category"])
        if cid is None:
            continue
        db.add(GearItem(
            user_id=user.id, category_id=cid, backpack_id=bp.id,
            name=item["name"], weight=item["weight_g"], quantity=item["quantity"],
            description="由背包预设自动创建",
        ))
        created += 1

    await db.flush()
    bp = await _load_bp(db, bp.id)
    return _serialize_backpack(bp)


@router.put("/{backpack_id}", response_model=BackpackResponse)
async def update_backpack(
    backpack_id: int,
    data: BackpackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Backpack).options(selectinload(Backpack.gear_items).selectinload(GearItem.category))
        .where(Backpack.id == backpack_id, Backpack.user_id == user.id)
    )
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404, "背包方案不存在")
    bp.name = data.name
    bp.description = data.description
    bp.base_weight = data.base_weight
    await db.flush()
    bp = await _load_bp(db, bp.id)
    return _serialize_backpack(bp)


@router.delete("/{backpack_id}")
async def delete_backpack(
    backpack_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Backpack).where(Backpack.id == backpack_id, Backpack.user_id == user.id)
    )
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404, "背包方案不存在")

    # 解绑装备（装备本身保留在用户库中）
    items = await db.execute(select(GearItem).where(GearItem.backpack_id == bp.id))
    for item in items.scalars().all():
        item.backpack_id = None

    await db.delete(bp)
    return {"success": True}


@router.post("/{backpack_id}/items/{gear_item_id}", response_model=BackpackResponse)
async def assign_item(
    backpack_id: int,
    gear_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """把用户的某件装备挂载到背包方案"""
    bp_result = await db.execute(
        select(Backpack).options(selectinload(Backpack.gear_items).selectinload(GearItem.category))
        .where(Backpack.id == backpack_id, Backpack.user_id == user.id)
    )
    bp = bp_result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404, "背包方案不存在")

    item_result = await db.execute(
        select(GearItem).where(GearItem.id == gear_item_id, GearItem.user_id == user.id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "装备不存在")

    item.backpack_id = bp.id
    await db.flush()
    bp = await _load_bp(db, bp.id)
    return _serialize_backpack(bp)


@router.delete("/{backpack_id}/items/{gear_item_id}", response_model=BackpackResponse)
async def unassign_item(
    backpack_id: int,
    gear_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bp_result = await db.execute(
        select(Backpack).options(selectinload(Backpack.gear_items).selectinload(GearItem.category))
        .where(Backpack.id == backpack_id, Backpack.user_id == user.id)
    )
    bp = bp_result.scalar_one_or_none()
    if not bp:
        raise HTTPException(404, "背包方案不存在")

    item_result = await db.execute(
        select(GearItem).where(GearItem.id == gear_item_id, GearItem.user_id == user.id,
                               GearItem.backpack_id == bp.id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "该装备不在本背包中")
    item.backpack_id = None
    await db.flush()
    bp = await _load_bp(db, bp.id)
    return _serialize_backpack(bp)
