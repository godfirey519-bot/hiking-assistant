"""共享依赖项"""
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.config import get_settings

security = HTTPBearer(auto_error=False)
settings = get_settings()


async def _decode_user_from_token(token: str, db: AsyncSession) -> User:
    """从 JWT token 解码并获取用户"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的认证凭证")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT token 获取当前用户（支持 Header 或 Query param）"""
    if token:
        return await _decode_user_from_token(token, db)
    if credentials:
        return await _decode_user_from_token(credentials.credentials, db)
    raise HTTPException(status_code=401, detail="未提供认证凭证")
