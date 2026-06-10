"""AI 对话 Agent —— 基于 LangGraph ReAct 模式，自动调用工具串联多步推理"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain.tools import tool

from shared.config import settings
from shared.logger import get_logger
from rag.vector_store import search as rag_search
from agents.hs_classifier.agent import HsClassifierAgent
from agents.tariff_calculator.agent import TariffCalculatorAgent
from agents.compliance_checker.agent import ComplianceCheckerAgent

logger = get_logger(__name__)

_llm: ChatOpenAI | None = None
_agent = None
_memory = MemorySaver()

SYSTEM_PROMPT = """你是一个跨境贸易与关税智能助手，帮助用户解答 HS 编码归类、关税计算、合规校验等问题。

你可以使用以下工具：
- search_knowledge: 搜索海关知识库，获取 HS 编码、税率、法规等知识
- classify_hs: 根据商品描述推理 HS 编码
- calculate_tariff: 计算目标国的进口税费
- check_compliance: 检查商品出口到目标国的合规风险

规则：
1. 用户问 HS 编码归类时，先用 classify_hs 推理，结果不理想再用 search_knowledge 补充
2. 用户问关税时，如果不知道 HS 编码，先归类再计算
3. 回答要简洁专业，税费用表格展示
4. 如果查询不到数据，明确告知用户"未查到数据，建议人工核实"
5. 用户缺少参数时主动追问，不要猜测；追问后用户说"跳转"/"算了"/"不提供了"，帮用户跳转：回复 [ACTION:redirect_xxx]（xxx 为 classify/tariff/compliance/pipeline/dashboard）
6. 用户主动要求跳转某个页面时，直接帮跳转
"""


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.llm_model or "qwen-plus",
            temperature=0.3,
            api_key=settings.llm_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _llm


@tool
async def search_knowledge(query: str) -> str:
    """搜索海关知识库，获取 HS 编码、税率、法规等专业知识。适合回答概念性问题、法规条款查询。"""
    docs = rag_search(query, k=3)
    if not docs:
        return "未在知识库中找到相关内容。"
    return "\n\n".join(
        f"[来源 {i+1}, 相似度 {d['distance']:.3f}] {d['document']}"
        for i, d in enumerate(docs)
    )


@tool
async def classify_hs(name: str, description: str = "", material: str = "", function: str = "") -> str:
    """根据商品信息推理 HS 编码。参数：name(商品名称), description(描述), material(材质), function(功能)。
    返回 HS 编码、置信度、推理路径。"""
    from domain.commodity import Commodity

    agent = HsClassifierAgent()
    commodity = Commodity(
        name=name,
        description=description or name,
        material=material,
        function=function,
    )
    result = await agent.run(commodity)
    alt_text = ""
    if result.alternatives:
        alts = [f"{a.code} ({a.description}, 置信度 {a.confidence:.0%})" for a in result.alternatives[:3]]
        alt_text = "\n备选编码：" + "；".join(alts)
    return (
        f"HS 编码：{result.code}\n"
        f"描述：{result.description}\n"
        f"置信度：{result.confidence:.0%}\n"
        f"推理路径：{' → '.join(result.reasoning_path)}"
        f"{alt_text}"
    )


@tool
async def calculate_tariff(hs_code: str, country: str = "US", declared_value: float = 0.0) -> str:
    """计算关税。参数：hs_code(HS编码), country(目标国家代码如US/EU/JP/KR/VN), declared_value(申报价值USD)。
    返回各项税费明细和总计。"""
    agent = TariffCalculatorAgent()
    result = await agent.run(hs_code=hs_code, country=country, declared_value=declared_value)

    if result.data_missing:
        header = "⚠️ 以下税率数据可能不完整，仅供参考：\n\n"
    else:
        header = ""

    lines = [header, f"目标国：{country} | HS 编码：{hs_code}", ""]
    for item in result.items:
        amount_str = f"${item.amount:.2f}" if item.amount is not None else "—"
        note = f" ({item.note})" if item.note else ""
        lines.append(f"• {item.name}：{item.rate}% → {amount_str}{note}")

    lines.append(f"\n综合税率：{result.total_rate}%")
    if result.total_amount is not None:
        lines.append(f"预估总税费：${result.total_amount:.2f}")
    if result.fta_applied:
        lines.append(f"FTA 优惠：适用于 {result.fta_applied}，预计节省 ${result.fta_saving:.2f}" if result.fta_saving else f"FTA 优惠：适用于 {result.fta_applied}")
    return "\n".join(lines)


@tool
async def check_compliance(name: str, country: str = "US", description: str = "", hs_code: str = "") -> str:
    """检查商品出口合规性。参数：name(商品名称), country(目标国家), description(描述), hs_code(HS编码，可选，不填则自动归类)。
    返回风险等级、违规项、许可证要求。"""
    from domain.commodity import Commodity

    commodity = Commodity(name=name, description=description or name)
    code = hs_code
    if not code:
        hs_agent = HsClassifierAgent()
        hs_result = await hs_agent.run(commodity)
        code = hs_result.code
    agent = ComplianceCheckerAgent()
    result = await agent.run(commodity=commodity, hs_code=code, country=country)

    risk_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(result.risk_level, "⚪")

    lines = [
        f"合规风险等级：{risk_emoji} {result.risk_level.upper()}",
        f"制裁命中：{'⚠️ 是' if result.sanctions_hit else '✅ 否'}",
        f"需要许可证：{'⚠️ 是' + (f'（{result.license_type}）' if result.license_type else '') if result.license_required else '✅ 否'}",
    ]
    if result.violations:
        lines.append("\n违规项：")
        for v in result.violations:
            lines.append(f"• [{v.severity.upper()}] {v.category}: {v.description}")
    if result.summary:
        lines.append(f"\n结论：{result.summary}")
    return "\n".join(lines)


def get_chat_agent():
    global _agent
    if _agent is None:
        llm = _get_llm()
        tools = [search_knowledge, classify_hs, calculate_tariff, check_compliance]
        _agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT, checkpointer=_memory)
    return _agent


async def chat(message: str, session_id: str) -> dict:
    """发送消息给对话 agent，返回回复。session_id 用于多轮记忆。"""
    agent = get_chat_agent()
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await agent.ainvoke(
            {"messages": [("user", message)]},
            config=config,
        )
        reply = result["messages"][-1].content
    except Exception as e:
        logger.error("chat.agent.error", error=str(e))
        reply = "抱歉，处理您的请求时遇到了问题，请稍后重试。"

    return {"reply": reply}
