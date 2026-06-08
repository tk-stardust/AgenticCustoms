"""RAG 检索器——将商品描述拆解为搜索查询，多轮检索后合并结果"""

from shared.llm import chat
from shared.logger import get_logger
from rag.vector_store import search

logger = get_logger(__name__)

DECOMPOSE_PROMPT = """你是一名外贸关务专家。根据以下商品描述，提取3个用于搜索HS编码的关键查询短语。
每个查询应聚焦于商品的一个关键特征（材质、功能、用途、工作原理等）。

商品描述：{description}

只输出3行查询短语，每行一个，不要编号，不要其他内容。"""


async def decompose_commodity(description: str) -> list[str]:
    """用 LLM 从商品描述中拆解出多个检索关键词

    :param description: 商品完整描述文本
    :returns: 最多 3 个聚焦不同特征的检索短语
    """
    messages = [{"role": "user", "content": DECOMPOSE_PROMPT.format(description=description)}]
    response = await chat(messages, temperature=0.1)
    queries = [line.strip() for line in response.strip().split("\n") if line.strip()]
    logger.info("retriever.decomposed", queries=queries)
    return queries[:3]


async def retrieve(commodity_description: str, k: int = 10) -> list[dict]:
    """对商品描述执行多轮语义检索，合并去重后返回 top-k 结果

    :param commodity_description: 商品描述文本
    :param k: 最终返回的文档数量上限
    :returns: 按相似度排序的文档列表，每项含 id/document/metadata/distance
    """
    queries = await decompose_commodity(commodity_description)
    # LLM 拆解可能遗漏关键信息，追加原始描述作为兜底查询
    queries.append(commodity_description)

    seen: set[str] = set()
    all_docs: list[dict] = []

    for query in queries:
        results = search(query, k=5)
        for doc in results:
            if doc["id"] not in seen:
                seen.add(doc["id"])
                all_docs.append(doc)

    all_docs.sort(key=lambda d: d["distance"])
    logger.info("retriever.done", total=len(all_docs))
    return all_docs[:k]
