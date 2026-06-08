"""数据库连接——异步引擎、会话工厂、自动建表"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from shared.config import settings

engine = create_async_engine(settings.mysql_url, echo=False)

# expire_on_commit=False 使对象在 commit 后属性仍可访问，无需 refresh
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """创建所有 ORM 表（CREATE TABLE IF NOT EXISTS，幂等）"""
    # 延迟导入避免 models 和 database 模块间的循环依赖
    from data.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
