"""种子数据入库——将 data.py 中的预置数据写入 MySQL

用法: python -m data.seed.runner
所有 seed_* 函数均按主键/联合键去重，可安全重复执行。
"""

import asyncio

from sqlalchemy import select

from data.db.database import async_session
from data.db.models import HsCode, TariffSchedule, SanctionEntry
from data.seed.data import HS_CODES, TARIFF_SCHEDULES, SANCTIONS


async def seed_hs_codes() -> int:
    """插入 HS 编码（按 code 去重，已存在则跳过）

    :returns: 本次新插入的条数
    """
    async with async_session() as session:
        existing = await session.execute(select(HsCode.code))
        existing_codes = set(existing.scalars().all())
        new_entries = [d for d in HS_CODES if d["code"] not in existing_codes]
        if not new_entries:
            return 0
        for item in new_entries:
            session.add(HsCode(**item))
        await session.commit()
        return len(new_entries)


async def seed_tariff_schedules() -> int:
    """插入关税税率（按 country + hs_code_prefix 联合键去重）

    :returns: 本次新插入的条数
    """
    async with async_session() as session:
        existing = await session.execute(
            select(TariffSchedule.country, TariffSchedule.hs_code_prefix)
        )
        existing_keys = set(existing.all())
        count = 0
        for item in TARIFF_SCHEDULES:
            key = (item["country"], item["hs_code_prefix"])
            if key not in existing_keys:
                session.add(TariffSchedule(**item))
                existing_keys.add(key)
                count += 1
        await session.commit()
        return count


async def seed_sanctions() -> int:
    """插入制裁实体（按 entity_name 去重）

    :returns: 本次新插入的条数
    """
    async with async_session() as session:
        existing = await session.execute(select(SanctionEntry.entity_name))
        existing_names = set(existing.scalars().all())
        count = 0
        for item in SANCTIONS:
            if item["entity_name"] not in existing_names:
                session.add(SanctionEntry(**item))
                count += 1
        await session.commit()
        return count


async def run_all() -> None:
    """依次执行三类种子数据写入，打印统计"""
    n_hs = await seed_hs_codes()
    n_tariff = await seed_tariff_schedules()
    n_sanction = await seed_sanctions()
    print(f"  HS codes:      {n_hs} new (total {len(HS_CODES)} defined)")
    print(f"  Tariff rules:  {n_tariff} new (total {len(TARIFF_SCHEDULES)} defined)")
    print(f"  Sanctions:     {n_sanction} new (total {len(SANCTIONS)} defined)")


if __name__ == "__main__":
    asyncio.run(run_all())
