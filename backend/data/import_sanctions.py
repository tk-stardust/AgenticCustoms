"""解析 OFAC SDN Enhanced XML → MySQL sanctions

结构: entities/entity/names/name(primary)/translations/translation/formattedFullName
用法: python -m data.import_sanctions
"""

import asyncio
import xml.etree.ElementTree as ET

from data.db.database import async_session
from data.db.models import SanctionEntry
from shared.logger import get_logger

logger = get_logger(__name__)
XML_PATH = "data/raw/sdn_enhanced.xml"
NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML"


async def import_sanctions(limit: int = 200):
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    entities_el = root.find(f"{{{NS}}}entities")
    if entities_el is None:
        return

    count = 0
    async with async_session() as session:
        for entity in list(entities_el):
            try:
                names_el = entity.find(f"{{{NS}}}names")
                if names_el is None:
                    continue
                # 取第一个 name（通常是主名）
                name_el = names_el.find(f"{{{NS}}}name")
                if name_el is None:
                    continue
                translations = name_el.find(f"{{{NS}}}translations")
                if translations is None:
                    continue
                trans = translations[0] if len(list(translations)) > 0 else None
                if trans is None:
                    continue
                form = trans.find(f"{{{NS}}}formattedFullName")
                name = form.text.strip() if form is not None and form.text else ""
                if not name:
                    continue

                country_el = entity.find(f"{{{NS}}}addresses")
                country = ""
                if country_el is not None and len(list(country_el)) > 0:
                    addr = list(country_el)[0]
                    c = addr.find(f"{{{NS}}}country")
                    country = c.text.strip() if c is not None and c.text else ""
            except (AttributeError, IndexError):
                continue

            session.add(SanctionEntry(
                entity_name=name,
                country=country,
                list_type="OFAC",
                restriction_type="prohibited",
                notes="OFAC SDN Enhanced",
            ))
            count += 1
            if count >= limit:
                break

        await session.commit()
    logger.info("import.sanctions.done", count=count)


if __name__ == "__main__":
    asyncio.run(import_sanctions(200))
