"""将 MySQL 中的 HS 编码同步到 Chroma 向量库
用法: python -m rag.seed
"""

import asyncio

from sqlalchemy import select

from data.db.database import async_session
from data.db.models import HsCode
from rag.vector_store import get_collection, add_documents
from rag.embedding import embed_texts
from shared.logger import get_logger

logger = get_logger(__name__)


def _build_doc(item: HsCode) -> str:
    return (
        f"HS编码 {item.code}：{item.description}，"
        f"第{item.chapter}章，品目{item.heading}，"
        f"基础税率 {item.base_rate}%，增值税 {item.vat_rate}%，"
        f"计量单位 {item.unit or '—'}"
    )


async def seed_chroma() -> int:
    collection = get_collection()

    async with async_session() as session:
        result = await session.execute(select(HsCode))
        rows = result.scalars().all()

    new_count = 0
    for row in rows:
        existing = collection.get(ids=[row.code])
        if existing["ids"]:
            continue  # 已存在，跳过
        doc = _build_doc(row)
        collection.add(
            ids=[row.code],
            documents=[doc],
            metadatas=[{
                "code": row.code,
                "chapter": row.chapter,
                "heading": row.heading,
                "base_rate": row.base_rate,
            }],
            embeddings=embed_texts([doc]),
        )
        new_count += 1

    logger.info("chroma.seed_done", new=new_count, total=len(rows))
    return new_count


if __name__ == "__main__":
    n = asyncio.run(seed_chroma())
    print(f"Chroma seeded: {n} new documents")
