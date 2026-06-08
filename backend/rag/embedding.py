"""嵌入模型管理——加载 bge-base-zh-v1.5，提供文本向量化接口"""

from sentence_transformers import SentenceTransformer

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)

# 全局单例：嵌入模型占用数百 MB 显存/内存，重复加载会 OOM
_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """获取嵌入模型单例，首次调用时加载模型，后续复用

    优先使用 settings.embedding_model_path 指定的本地路径，
    为空时用 settings.embedding_model 的 HuggingFace 模型名自动下载。
    """
    global _model
    if _model is None:
        path = settings.embedding_model_path or settings.embedding_model
        logger.info("embedding.loading", path=path)
        _model = SentenceTransformer(path)
        logger.info("embedding.loaded")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """将文本列表批量转换为归一化向量

    :param texts: 待嵌入的文本列表
    :returns: 归一化后的向量列表，每个向量维度由模型决定（bge-base 为 768）
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
