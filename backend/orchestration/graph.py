"""全流程编排图——HS 归类 → 并行（关税/合规/原产地）→ 申报文件生成"""

import asyncio
import json
from typing import AsyncGenerator

from langgraph.graph import StateGraph, END

from orchestration.state import PipelineState
from agents.hs_classifier.agent import HsClassifierAgent
from agents.tariff_calculator.agent import TariffCalculatorAgent
from agents.compliance_checker.agent import ComplianceCheckerAgent
from agents.origin_matcher.agent import OriginMatcherAgent
from agents.doc_generator.agent import DocGeneratorAgent
from shared.logger import get_logger

logger = get_logger(__name__)


async def classify_node(state: PipelineState) -> dict:
    """步骤1：HS 编码归类"""
    agent = HsClassifierAgent()
    result = await agent.run(state["commodity"])
    return {"hs_result": result}


async def tariff_node(state: PipelineState) -> dict:
    """步骤2a：关税计算"""
    agent = TariffCalculatorAgent()
    result = await agent.run(state["hs_result"].code, state["target_country"])
    return {"tariff_result": result}


async def compliance_node(state: PipelineState) -> dict:
    """步骤2b：合规校验"""
    agent = ComplianceCheckerAgent()
    result = await agent.run(
        state["commodity"], state["hs_result"].code, state["target_country"]
    )
    return {"compliance_result": result}


async def origin_node(state: PipelineState) -> dict:
    """步骤2c：原产地匹配"""
    agent = OriginMatcherAgent()
    result = await agent.run(state["hs_result"].code, state["target_country"])
    return {"origin_result": result}


async def parallel_nodes(state: PipelineState) -> dict:
    """并行执行关税、合规、原产地三个 Agent"""
    results = await asyncio.gather(
        tariff_node(state),
        compliance_node(state),
        origin_node(state),
    )
    merged = {}
    for r in results:
        merged.update(r)
    return merged


async def document_node(state: PipelineState) -> dict:
    """步骤3：生成申报文件 + 交叉校验"""
    agent = DocGeneratorAgent()
    result = await agent.run(
        state["commodity"],
        state["hs_result"],
        state["tariff_result"],
        state["compliance_result"],
        state["origin_result"],
    )
    return {"documents": result}


def build_pipeline_graph() -> StateGraph:
    """构建全流程编排图

    拓扑：classify → parallel（关税 + 合规 + 原产地）→ document → END
    """
    graph = StateGraph(PipelineState)

    graph.add_node("classify", classify_node)
    graph.add_node("parallel", parallel_nodes)
    graph.add_node("document", document_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "parallel")
    graph.add_edge("parallel", "document")
    graph.add_edge("document", END)

    return graph.compile()


async def run_pipeline(commodity, target_country: str):
    """执行全流程流水线

    :param commodity: Commodity 商品实体
    :param target_country: 目标国家代码
    :returns: 最终的 DeclarationDoc
    """
    logger.info("pipeline.start", name=commodity.name, country=target_country)
    app = build_pipeline_graph()
    final_state = await app.ainvoke({
        "commodity": commodity,
        "target_country": target_country,
    })
    logger.info("pipeline.done")
    return {
        "documents": final_state["documents"],
        "hs_result": final_state["hs_result"],
        "tariff_result": final_state["tariff_result"],
        "compliance_result": final_state["compliance_result"],
        "origin_result": final_state["origin_result"],
    }


async def run_pipeline_stream(commodity, target_country: str) -> AsyncGenerator[str, None]:
    """流式执行全流程，逐 Agent 推送 SSE 进度事件

    :param commodity: Commodity 商品实体
    :param target_country: 目标国家代码
    :yields: SSE 格式字符串（event + data）
    """
    logger.info("pipeline_stream.start", name=commodity.name, country=target_country)

    # Step 1: HS 归类
    yield _sse("progress", {"agent": 0, "message": "HS编码推理中..."})
    hs_agent = HsClassifierAgent()
    hs_result = await hs_agent.run(commodity)
    yield _sse("progress", {"agent": 0, "done": True, "code": hs_result.code, "confidence": hs_result.confidence})

    # Step 2-4: 并行（关税 + 合规 + 原产地）
    yield _sse("progress", {"agent": 1, "message": "关税计算中..."})
    yield _sse("progress", {"agent": 2, "message": "合规校验中..."})
    yield _sse("progress", {"agent": 3, "message": "原产地匹配中..."})

    tariff_agent = TariffCalculatorAgent()
    compliance_agent = ComplianceCheckerAgent()
    origin_agent = OriginMatcherAgent()
    tariff_result, compliance_result, origin_result = await asyncio.gather(
        tariff_agent.run(hs_result.code, target_country),
        compliance_agent.run(commodity, hs_result.code, target_country),
        origin_agent.run(hs_result.code, target_country),
    )
    yield _sse("progress", {"agent": 1, "done": True})
    yield _sse("progress", {"agent": 2, "done": True, "risk_level": compliance_result.risk_level.value})
    yield _sse("progress", {"agent": 3, "done": True})

    # Step 5: 申报文件生成
    yield _sse("progress", {"agent": 4, "message": "生成申报文件中..."})
    doc_agent = DocGeneratorAgent()
    doc = await doc_agent.run(commodity, hs_result, tariff_result, compliance_result, origin_result)
    yield _sse("progress", {"agent": 4, "done": True})

    # 完成
    logger.info("pipeline_stream.done")
    yield _sse("done", {
        "documents": doc.model_dump(),
        "tariff_result": tariff_result.model_dump(),
        "compliance_result": compliance_result.model_dump(),
        "origin_result": origin_result.model_dump(),
    })


def _sse(event: str, data: dict) -> str:
    """构造一条 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
