"""解析中国海关 2026 年进出口税则 Excel → MySQL + Chroma

用法：python -m data.import_china
"""

import asyncio
import re

import pandas as pd

from data.db.database import async_session
from data.db.models import HsCode
from rag.vector_store import get_collection
from rag.embedding import embed_texts
from shared.logger import get_logger

logger = get_logger(__name__)
XLSX_PATH = "data/raw/hscode2026.xlsx"

# 列索引（0-based，Excel 无表头行）
COL_CODE = 0       # HS 编码
COL_DESC = 1       # 商品描述
COL_IMPORT = 5     # 进口关税税率
COL_VAT = 11       # 增值税率
COL_UNIT1 = 3      # 第一计量单位


def _parse_rate(val) -> float:
    """'10%' → 10.0, '-' → 0.0"""
    s = str(val).strip().replace("%", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


async def import_china(limit: int = 500):
    df = pd.read_excel(XLSX_PATH, header=None)
    logger.info("import.china.loaded", rows=len(df))

    # 按章节均匀取样，保证覆盖全品类
    items = []
    seen_chapters: dict[str, int] = {}
    for _, row in df.iterrows():
        code = str(row[COL_CODE]).strip().replace(".", "")
        if not re.match(r"^\d{8,10}$", code):
            continue
        chapter = code[:2]
        # 每章最多取 limit//98 条，覆盖更多章节
        max_per_chapter = max(1, limit // 98)
        if seen_chapters.get(chapter, 0) >= max_per_chapter:
            continue
        seen_chapters[chapter] = seen_chapters.get(chapter, 0) + 1
        items.append({
            "code": code[:10],
            "description": str(row[COL_DESC]).strip(),
            "chapter": chapter,
            "heading": code[:4],
            "country": "CN",
            "base_rate": _parse_rate(row[COL_IMPORT]),
            "vat_rate": _parse_rate(row[COL_VAT]),
            "unit": str(row[COL_UNIT1]).strip() if pd.notna(row[COL_UNIT1]) else None,
        })
        if len(items) >= limit:
            break

    logger.info("import.china.parsed", count=len(items))

    # MySQL — 去重插入
    async with async_session() as session:
        from sqlalchemy import select as _select
        existing = await session.execute(_select(HsCode.code))
        existing_codes = set(existing.scalars().all())
        new_items = [it for it in items if it["code"] not in existing_codes]
        for item in new_items:
            session.add(HsCode(**item))
        await session.commit()
        logger.info("import.china.mysql", new=len(new_items), skipped=len(items)-len(new_items))

    # Chroma — 只嵌入新增数据
    if new_items:
        collection = get_collection()
        for item in new_items:
            doc = f"HS编码 {item['code']}：{item['description']}，第{item['chapter']}章，进口关税 {item['base_rate']}%，增值税 {item['vat_rate']}%"
            collection.add(
                ids=[item["code"]],
                documents=[doc],
                metadatas=[{"code": item["code"], "chapter": item["chapter"], "heading": item["heading"], "base_rate": item["base_rate"]}],
                embeddings=embed_texts([doc]),
            )

    logger.info("import.china.done", count=len(items))


if __name__ == "__main__":
    asyncio.run(import_china(500))
