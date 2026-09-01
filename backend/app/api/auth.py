from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ChangePasswordRequest,
    MessageResponse,
)
from app.config import get_settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

RESET_TOKEN_EXPIRE_MINUTES = 30
MIN_PASSWORD_LENGTH = 6


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_reset_token(user_id: int) -> str:
    """短时效（30 分钟）密码重置凭证，type 标记防止被当作登录 token 使用"""
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "type": "password_reset", "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> int:
    """解码重置 token 并返回 user_id，失败抛 400"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "password_reset":
            raise HTTPException(400, "重置链接无效")
        return int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(400, "重置链接无效或已过期")


def validate_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"密码长度不能少于 {MIN_PASSWORD_LENGTH} 位")


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # 检查用户名
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")

    # 检查邮箱
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "邮箱已注册")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=pwd_context.hash(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")

    token = create_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """按邮箱发起密码重置。开发模式（debug=True）直接返回 token，生产走邮件。"""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        # 不泄露邮箱是否已注册
        return ForgotPasswordResponse(message="如果该邮箱已注册，重置凭证已生成")

    token = create_reset_token(user.id)
    if settings.debug:
        # 开发模式：无 SMTP，token 直接返回给前端展示
        return ForgotPasswordResponse(
            message="开发模式：重置凭证已生成，点击下方链接重置密码",
            reset_token=token,
        )
    # 生产模式：TODO 接入 SMTP 发送邮件
    return ForgotPasswordResponse(message="重置邮件已发送，请查收邮箱")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """用重置凭证设置新密码"""
    validate_new_password(data.new_password)
    user_id = decode_reset_token(data.token)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "用户不存在")

    user.hashed_password = pwd_context.hash(data.new_password)
    await db.commit()
    return MessageResponse(message="密码已重置，请用新密码登录")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码：需验证当前密码"""
    validate_new_password(data.new_password)
    if not pwd_context.verify(data.current_password, user.hashed_password):
        raise HTTPException(400, "当前密码错误")

    user.hashed_password = pwd_context.hash(data.new_password)
    await db.commit()
    return MessageResponse(message="密码修改成功")
