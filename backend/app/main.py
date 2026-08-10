from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import get_settings, MEDIA_DIR
from app.database import init_db
from app.api import auth, routes, equipment, plans, trips, agents, chat, stats

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时清理资源


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(trips.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

# 媒体文件静态服务 (徒步记录照片/视频，存于 data/media)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
