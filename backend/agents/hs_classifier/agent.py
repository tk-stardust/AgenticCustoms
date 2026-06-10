"""HS 编码归类智能体——RAG 检索 + LLM 推理合成"""

import json
import uuid

from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from agents.base import BaseAgent
from rag.retriever import retrieve
from rag.vector_store import get_collection
from rag.embedding import embed_texts
from shared.llm import chat
from shared.logger import get_logger

logger = get_logger(__name__)

CLASSIFY_PROMPT = """你是一名资深外贸关务专家，精通《商品名称及编码协调制度》（HS公约）和WCO注释。

## 任务
根据商品描述和检索到的候选HS编码，确定最可能的HS编码（前6位国际通用码），给出推理过程和置信度。

## 商品信息
名称：{name}
描述：{description}
材质：{material}
功能：{function}
用途：{usage}

## 候选HS编码（从知识库检索）
{candidates}

## 要求
1. 分析商品的关键归类特征（材质、功能、用途、工作原理）
2. 对照候选编码，选出最匹配的HS编码
3. 给出推理步骤链（至少3步）
4. 标注引用的条文或规则来源
5. 评估置信度（0.0-1.0）

## 输出格式（严格JSON）
```json
{{
  "code": "6位HS编码",
  "description": "品目描述",
  "confidence": 0.85,
  "reasoning_path": ["步骤1: ...", "步骤2: ...", "步骤3: ..."],
  "citations": ["来源1: ...", "来源2: ..."]
}}
```"""


class HsClassifierAgent(BaseAgent[HsCodeResult]):
    """HS 编码推理智能体——RAG 检索候选编码 + LLM 推理合成最佳匹配"""

    async def run(self, commodity: Commodity) -> HsCodeResult:
        """执行 HS 编码归类流程

        :param commodity: 待归类的商品实体
        :returns: HS 编码结果，含编码、置信度、推理路径、条文溯源
        """
        self.validate_input(commodity=commodity)
        logger.info("hs_classifier.start", name=commodity.name)

        query = commodity.to_rag_query()
        docs = await retrieve(query, k=8)

        if not docs:
            return HsCodeResult(
                code="000000",
                description="未找到匹配的HS编码",
                confidence=0.0,
                reasoning_path=["知识库中无相关编码"],
                citations=[],
            )

        candidates = "\n".join(f"- {d['document']}" for d in docs)

        # temperature=0.1 保证归类确定性，HS 编码不允许随机猜测
        prompt = CLASSIFY_PROMPT.format(
            name=commodity.name,
            description=commodity.description,
            material=commodity.material or "未知",
            function=commodity.function or "未知",
            usage=commodity.usage or "未知",
            candidates=candidates,
        )
        messages = [{"role": "user", "content": prompt}]
        response = await chat(messages, temperature=0.1, max_tokens=1024)

        result = self._parse_response(response)
        self.validate_output(result)
        logger.info("hs_classifier.done", code=result.code, confidence=result.confidence)

        # 归类成功 → 写入 Chroma，后续检索可命中历史案例
        if result.confidence > 0.5 and result.code != "000000":
            try:
                doc = f"HS编码 {result.code}：{result.description}（{commodity.name}，{commodity.description}）"
                col = get_collection()
                import uuid
                col.add(
                    ids=[f"hist_{result.code}_{uuid.uuid4().hex[:6]}"],
                    documents=[doc],
                    metadatas=[{"code": result.code, "source": "history"}],
                    embeddings=embed_texts([doc]),
                )
                logger.info("hs_classifier.cached", code=result.code)
            except Exception as e:
                logger.warning("hs_classifier.cache_failed", error=str(e))

        return result

    def _parse_response(self, response: str) -> HsCodeResult:
        """从 LLM 响应中提取 JSON 并解析为 HsCodeResult

        :param response: LLM 原始回复文本，可能包裹在 ```json 代码块中
        """
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 解析失败时返回退化结果，前端据此区分"无匹配"和"格式异常"
            logger.warning("hs_classifier.parse_failed", response=response[:200])
            return HsCodeResult(
                code="000000",
                description="LLM返回格式异常",
                confidence=0.0,
                reasoning_path=[response[:300]],
                citations=[],
            )
        return HsCodeResult(**data)

    def validate_input(self, **kwargs) -> None:
        """前置校验：商品描述不能为空"""
        commodity = kwargs.get("commodity")
        if not commodity or not commodity.description:
            raise ValueError("commodity.description is required")

    def validate_output(self, result: HsCodeResult) -> bool:
        """后置校验：HS 编码至少 6 位，置信度在 0~1 之间"""
        if not result.code or len(result.code) < 6:
            return False
        if result.confidence < 0.0 or result.confidence > 1.0:
            return False
        return True
