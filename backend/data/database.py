from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from shared.config import settings

engine = create_async_engine(settings.mysql_url, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from data.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
