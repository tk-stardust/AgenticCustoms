"""Chroma 向量库封装——持久化存储 HS 编码文档，提供语义搜索"""

import chromadb

# Chroma 1.5.x 中 PersistentClient() 是工厂函数而非类，类型标注需用 Client
from chromadb.api.client import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)

_client: ChromaClient | None = None


def get_client() -> ChromaClient:
    """获取 Chroma 持久化客户端单例"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    """获取或创建 Collection——余弦距离适合语义相似度搜索"""
    return get_client().get_or_create_collection(
        name=settings.chroma_collection,
        # 默认 l2 距离对高维文本嵌入效果差，cosine 是标准选择
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
    """向向量库批量添加文档（自动向量化）

    :param ids: 文档唯一标识列表，与 texts 一一对应
    :param texts: 文档文本列表
    :param metadatas: 文档元数据列表，如 {"code": "8517.12", "chapter": "85"}
    """
    # 延迟导入：避免模块加载时就初始化嵌入模型
    from rag.embedding import embed_texts
    collection = get_collection()
    embeddings = embed_texts(texts)
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    logger.info("chroma.added", count=len(ids))


def search(query: str, k: int = 10) -> list[dict]:
    """语义搜索——将查询文本向量化后返回最相似的 k 个文档

    :param query: 查询文本
    :param k: 返回文档数量上限
    :returns: 文档列表，每项含 id、document、metadata、distance，按相似度降序
    """
    # 延迟导入：避免模块加载时就初始化嵌入模型
    from rag.embedding import embed_texts
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=k)

    # 将 Chroma 的嵌套列表格式转为 dict 列表，方便下游使用
    docs: list[dict] = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            docs.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })
    return docs
