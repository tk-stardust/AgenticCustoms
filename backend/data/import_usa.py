"""解析美国 HTS CSV → MySQL tariff_schedules

用法：python -m data.import_usa
"""

import asyncio
import csv
import re

from sqlalchemy import select as _select

from data.db.database import async_session
from data.db.models import TariffSchedule
from shared.logger import get_logger

logger = get_logger(__name__)
CSV_PATH = "data/raw/hts_2026_revision_9_csv.csv"


def _read_csv():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _parse_rate(val: str) -> float:
    """'Free' → 0.0, '5.5%' → 5.5, 'The duty ... + 25%' → 25.0"""
    if not val:
        return 0.0
    val = val.strip()
    if val.lower() == "free":
        return 0.0
    rate_m = re.search(r"(\d+(?:\.\d+)?)\s*%?", val)
    return float(rate_m.group(1)) if rate_m else 0.0


def _parse_fta_name(special: str) -> str | None:
    """从 Special Rate 提取 FTA 名称。如 'Free (A+,AU,BH,CL,...)' → 'US FTA Programs'"""
    if not special or special.lower() == "free":
        return None
    codes_m = re.search(r"\(([A-Z+,]+)\)", special)
    if codes_m:
        return f"US FTA ({codes_m.group(1).strip('+')})"
    return None


async def import_usa(limit: int = 5000):
    logger.info("import.usa.scanning")
    count = 0
    async with async_session() as session:
        existing = await session.execute(
            _select(TariffSchedule.hs_code_prefix).where(TariffSchedule.country == "US")
        )
        existing_prefixes = set(existing.scalars().all())

        for row in _read_csv():
            hs_code = (row.get("HTS Number") or "").strip().replace(".", "")
            if not hs_code or len(hs_code) < 6:
                continue
            prefix = hs_code[:6]
            if prefix in existing_prefixes:
                continue
            existing_prefixes.add(prefix)

            desc = (row.get("Description") or "").strip()
            base_rate = _parse_rate(row.get("General Rate of Duty") or "")
            special = (row.get("Special Rate of Duty") or "").strip()
            additional = (row.get("Additional Duties") or "").strip()

            # FTA 优惠税率（最多 195 字符，留余量）
            pref_rate = _parse_rate(special) if special else None
            fta_name = None
            if special and pref_rate is not None:
                raw_fta = _parse_fta_name(special)
                fta_name = raw_fta[:195] if raw_fta else None

            # 反倾销 / 附加税
            anti_rate = _parse_rate(additional) if additional else 0.0

            notes_parts = [desc[:100]]
            if special:
                notes_parts.append(f"(Special: {special[:80]})")
            anti_note = f"⚠ 附加税 {anti_rate}%" if anti_rate > 0 else ""
            if additional and anti_rate == 0:
                anti_note = f"附加: {additional[:80]}"

            session.add(TariffSchedule(
                country="US",
                hs_code_prefix=prefix,
                base_rate=base_rate,
                vat_rate=0.0,
                anti_dumping_rate=anti_rate,
                preferential_rate=pref_rate,
                fta_name=fta_name,
                notes=" | ".join(filter(None, notes_parts)),
            ))
            count += 1
            if count >= limit:
                break

        await session.commit()
    logger.info("import.usa.done", count=count)


if __name__ == "__main__":
    asyncio.run(import_usa(5000))
