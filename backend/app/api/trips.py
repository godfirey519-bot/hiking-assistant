from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import aiofiles
from datetime import datetime

from app.config import MEDIA_DIR
from app.database import get_db
from app.models.user import User
from app.models.trip import TripRecord, TripMedia
from app.schemas.trip import TripCreate, TripResponse, TripMediaResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/trips", tags=["徒步记录"])


@router.get("/", response_model=list[TripResponse])
async def list_trips(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TripRecord)
        .where(TripRecord.user_id == user.id)
        .order_by(TripRecord.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=None)
async def create_trip(
    data: TripCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trip = TripRecord(
        user_id=user.id,
        title=data.title,
        description=data.description,
        plan_id=data.plan_id,
        route_id=data.route_id,
        actual_distance=data.actual_distance,
        actual_elevation_gain=data.actual_elevation_gain,
        rating=data.rating,
        notes=data.notes,
        weather=data.weather,
        start_date=datetime.fromisoformat(data.start_date) if data.start_date else None,
        end_date=datetime.fromisoformat(data.end_date) if data.end_date else None,
    )
    db.add(trip)
    await db.flush()
    await db.refresh(trip)
    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "plan_id": trip.plan_id,
        "route_id": trip.route_id,
        "title": trip.title,
        "description": trip.description,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "end_date": trip.end_date.isoformat() if trip.end_date else None,
        "actual_distance": trip.actual_distance,
        "actual_elevation_gain": trip.actual_elevation_gain,
        "rating": trip.rating,
        "notes": trip.notes,
        "weather": trip.weather,
        "media": [],
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
    }


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TripRecord).where(TripRecord.id == trip_id, TripRecord.user_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "记录不存在")
    return trip


@router.delete("/{trip_id}")
async def delete_trip(
    trip_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TripRecord).where(TripRecord.id == trip_id, TripRecord.user_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "记录不存在")
    await db.delete(trip)
    return {"success": True}


@router.post("/{trip_id}/upload-media", response_model=TripMediaResponse)
async def upload_media(
    trip_id: int,
    file: UploadFile = File(...),
    description: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传照片/视频到徒步记录"""
    # 验证记录存在
    result = await db.execute(
        select(TripRecord).where(TripRecord.id == trip_id, TripRecord.user_id == user.id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404, "记录不存在")

    # 判断文件类型
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
        file_type = "image"
    elif ext in ('.mp4', '.mov', '.avi', '.mkv', '.webm'):
        file_type = "video"
    else:
        raise HTTPException(400, f"不支持的文件格式: {ext}")

    # 保存文件到 MEDIA_DIR/{trip_id}/，file_path 存相对路径（对应 /media URL）
    import uuid
    trip_media_dir = MEDIA_DIR / str(trip_id)
    trip_media_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    absolute_path = trip_media_dir / safe_name
    relative_path = f"{trip_id}/{safe_name}"

    async with aiofiles.open(absolute_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    media = TripMedia(
        trip_id=trip_id,
        file_type=file_type,
        file_path=relative_path,
        description=description,
    )
    db.add(media)
    await db.flush()
    await db.refresh(media)
    return media
