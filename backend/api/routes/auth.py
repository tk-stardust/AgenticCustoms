"""认证接口——注册、登录、获取当前用户"""

from datetime import datetime, timedelta, timezone

import bcrypt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from jose import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.deps import require_user
from data.db.database import async_session
from data.db.models import User
from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class AuthResponse(BaseModel):
    token: str
    username: str


def _create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"user_id": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/register", response_model=AuthResponse)
async def register(req: AuthRequest):
    """注册新用户"""
    async with async_session() as db:
        existing = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user = User(username=req.username, password_hash=_hash_pw(req.password))
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="用户名已存在")
        await db.refresh(user)
        logger.info("auth.register", username=req.username)
        return AuthResponse(token=_create_token(user.id), username=user.username)


@router.post("/login", response_model=AuthResponse)
async def login(req: AuthRequest):
    """登录"""
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
        if not user or not _verify_pw(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        logger.info("auth.login", username=req.username)
        return AuthResponse(token=_create_token(user.id), username=user.username)


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=4, max_length=100)
    new_password: str = Field(..., min_length=4, max_length=100)


@router.put("/auth/password")
async def change_password(req: PasswordChange, user: User = Depends(require_user)):
    """修改密码"""
    if not _verify_pw(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    async with async_session() as db:
        u = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
        u.password_hash = _hash_pw(req.new_password)
        await db.commit()
    logger.info("auth.password_changed", username=user.username)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(require_user)):
    """获取当前登录用户信息"""
    return {"username": user.username}
