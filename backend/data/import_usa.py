"""解析美国 HTS CSV → MySQL tariff_schedules

用法：python -m data.import_usa
"""

import asyncio
import csv
import re

from data.db.database import async_session
from data.db.models import TariffSchedule
from shared.logger import get_logger

logger = get_logger(__name__)
CSV_PATH = "data/raw/hts_2026_revision_9_csv.csv"


def _read_csv():
    with open(CSV_PATH, encoding="utf-8-sig") as f:  # utf-8-sig 自动去掉 BOM
        reader = csv.DictReader(f)
        for row in reader:
            yield row


async def import_usa(limit: int = 300):
    logger.info("import.usa.scanning")
    count = 0
    async with async_session() as session:
        for row in _read_csv():
            hs_code = (row.get("HTS Number") or "").strip().replace(".", "")
            if not hs_code or len(hs_code) < 10:  # 取完整10位编码如 0101.21.00.10
                continue

            desc = (row.get("Description") or "").strip()
            rate_str = (row.get("General Rate of Duty") or "Free").strip()
            if rate_str.lower() == "free":
                base_rate = 0.0
            else:
                rate_m = re.search(r"(\d+(?:\.\d+)?)\s*%?", str(rate_str))
                base_rate = float(rate_m.group(1)) if rate_m else 0.0

            session.add(TariffSchedule(
                country="US",
                hs_code_prefix=hs_code[:6],
                base_rate=base_rate,
                vat_rate=0.0,
                notes=f"{desc[:150]} (General Rate: {rate_str})",
            ))
            count += 1
            if count >= limit:
                break

        await session.commit()
    logger.info("import.usa.done", count=count)


if __name__ == "__main__":
    asyncio.run(import_usa(300))
