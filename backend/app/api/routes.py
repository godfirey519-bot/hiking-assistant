from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import gpxpy
import aiofiles
import os

from app.database import get_db
from app.models.user import User
from app.models.route import Route, RouteWaypoint
from app.schemas.route import RouteCreate, RouteResponse, RouteDetailResponse, GPXUploadResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/routes", tags=["路线"])


@router.get("/", response_model=list[RouteResponse])
async def list_routes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.user_id == user.id).order_by(Route.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=RouteResponse)
async def create_route(
    data: RouteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    route = Route(user_id=user.id, **data.model_dump())
    db.add(route)
    await db.flush()
    await db.refresh(route)
    return route


@router.get("/{route_id}", response_model=RouteDetailResponse)
async def get_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.id == route_id, Route.user_id == user.id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "路线不存在")

    # 获取 waypoints
    wp_result = await db.execute(
        select(RouteWaypoint)
        .where(RouteWaypoint.route_id == route_id)
        .order_by(RouteWaypoint.point_order)
    )
    waypoints = wp_result.scalars().all()

    return RouteDetailResponse(
        **{k: getattr(route, k) for k in RouteResponse.model_fields},
        waypoints=[
            {"lat": w.latitude, "lng": w.longitude, "ele": w.elevation, "name": w.name}
            for w in waypoints
        ],
    )


@router.delete("/{route_id}")
async def delete_route(
    route_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Route).where(Route.id == route_id, Route.user_id == user.id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "路线不存在")
    await db.delete(route)
    return {"success": True}


@router.post("/upload-gpx", response_model=GPXUploadResponse)
async def upload_gpx(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传并解析 GPX 文件"""
    if not file.filename or not file.filename.endswith('.gpx'):
        raise HTTPException(400, "请上传 .gpx 格式的文件")

    content = await file.read()
    try:
        gpx = gpxpy.parse(content.decode('utf-8'))
    except Exception as e:
        raise HTTPException(400, f"GPX 文件解析失败: {str(e)}")

    # 保存文件
    upload_dir = os.path.join("..", "data", "gpx")
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = file.filename.replace(" ", "_")
    file_path = os.path.join(upload_dir, f"{user.id}_{safe_name}")
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # 计算统计信息
    track_points = []
    elevation_gain = 0.0
    elevation_loss = 0.0
    max_ele = 0.0
    min_ele = float('inf')
    total_distance = 0.0

    for track in gpx.tracks:
        for segment in track.segments:
            points = segment.points
            for i, pt in enumerate(points):
                track_points.append(pt)
                if pt.elevation is not None:
                    max_ele = max(max_ele, pt.elevation)
                    min_ele = min(min_ele, pt.elevation)
                    if i > 0 and points[i-1].elevation is not None:
                        diff = pt.elevation - points[i-1].elevation
                        if diff > 0:
                            elevation_gain += diff
                        else:
                            elevation_loss += abs(diff)

    if min_ele == float('inf'):
        min_ele = 0

    total_distance = gpx.length_3d() or 0

    # 推断难度
    if total_distance < 10000 and elevation_gain < 500:
        difficulty = "easy"
    elif total_distance < 20000 and elevation_gain < 1000:
        difficulty = "moderate"
    elif total_distance < 30000 and elevation_gain < 2000:
        difficulty = "hard"
    else:
        difficulty = "expert"

    # 从文件名推断路线名称
    name = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ")

    route = Route(
        user_id=user.id,
        name=name,
        distance=total_distance,
        elevation_gain=elevation_gain,
        elevation_loss=elevation_loss,
        max_elevation=max_ele,
        min_elevation=min_ele,
        difficulty=difficulty,
        duration_days=max(1, int(total_distance / 20000) + 1),
        gpx_file_path=file_path,
        start_point=f"{track_points[0].latitude:.6f},{track_points[0].longitude:.6f}" if track_points else "",
        end_point=f"{track_points[-1].latitude:.6f},{track_points[-1].longitude:.6f}" if track_points else "",
    )
    db.add(route)
    await db.flush()

    # 存储轨迹点（采样以减少数据量）
    sample_rate = max(1, len(track_points) // 500)
    for i, pt in enumerate(track_points):
        if i % sample_rate == 0:
            wp = RouteWaypoint(
                route_id=route.id,
                latitude=pt.latitude,
                longitude=pt.longitude,
                elevation=pt.elevation,
                timestamp=pt.time,
                point_order=i,
            )
            db.add(wp)

    await db.refresh(route)

    # 构建返回
    wp_result = await db.execute(
        select(RouteWaypoint)
        .where(RouteWaypoint.route_id == route.id)
        .order_by(RouteWaypoint.point_order)
    )
    waypoints = wp_result.scalars().all()

    return GPXUploadResponse(
        success=True,
        route=RouteDetailResponse(
            **{k: getattr(route, k) for k in RouteResponse.model_fields},
            waypoints=[
                {"lat": w.latitude, "lng": w.longitude, "ele": w.elevation, "name": w.name}
                for w in waypoints
            ],
        ),
        waypoint_count=len(waypoints),
    )
