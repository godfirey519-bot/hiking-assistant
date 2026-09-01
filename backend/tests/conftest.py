"""pytest 公共配置：隔离测试数据库 + ASGI 客户端夹具。

重要：环境变量必须在导入 app 模块之前设置（database.py 在模块级创建 engine）。
"""
import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BACKEND_DIR / "data" / "test_hiking.db"

# 隔离测试数据库与外部依赖（先于任何 app 导入）
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["DEEPSEEK_API_KEY"] = "test-key"
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["DEBUG"] = "true"
os.environ["SMTP_HOST"] = ""

sys.path.insert(0, str(BACKEND_DIR))

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """每个测试会话用全新的测试库"""
    if TEST_DB.exists():
        TEST_DB.unlink()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 会话结束后清理（保留文件便于排查，由 .gitignore 忽略）


@pytest_asyncio.fixture
async def client():
    """ASGI 测试客户端（不触发 lifespan，表已由 setup_test_db 创建）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _register_and_login(client: AsyncClient, username: str, password: str = "testpass123"):
    """注册并登录，返回 (headers, user_id)"""
    email = f"{username}@test.com"
    r = await client.post("/api/auth/register", json={
        "username": username, "email": email, "password": password,
    })
    if r.status_code != 200:
        r = await client.post("/api/auth/login", json={"username": username, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, r.json()["user"]["id"]


@pytest_asyncio.fixture
async def auth_headers(client):
    """唯一测试用户的认证头"""
    uname = f"user_{uuid.uuid4().hex[:10]}"
    headers, user_id = await _register_and_login(client, uname)
    return {"headers": headers, "user_id": user_id, "username": uname}


@pytest_asyncio.fixture
async def second_user(client):
    """第二个用户（用于权限隔离测试）"""
    uname = f"user2_{uuid.uuid4().hex[:10]}"
    headers, user_id = await _register_and_login(client, uname)
    return {"headers": headers, "user_id": user_id, "username": uname}
