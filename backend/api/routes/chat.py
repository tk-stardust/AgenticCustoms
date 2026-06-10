"""AI 对话接口 —— 意图分类 + ReAct Agent + 历史记录"""

import json
import uuid

from fastapi import APIRouter, Depends
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select, delete

from agents.chat.agent import chat as chat_agent
from api.deps import require_user
from data.db.database import async_session
from data.db.models import ChatMessage, User
from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# 意图分类——独立 LLM，temperature=0 保证稳定
_intent_llm: ChatOpenAI | None = None

INTENT_PROMPT = """判断用户意图，只输出 JSON，不要其他内容：
- HS 归类/查询编码 → {"action":"redirect","page":"classify","label":"HS 归类"}
- 关税计算/税率查询 → {"action":"redirect","page":"tariff","label":"关税计算"}
- 合规校验/风险检查/禁限品 → {"action":"redirect","page":"compliance","label":"合规校验"}
- 生成申报文件/下载报告/打印PDF → {"action":"redirect","page":"pipeline","label":"一键全流程","force":true}
- 查看风险看板/数据统计/图表 → {"action":"redirect","page":"dashboard","label":"风险看板"}
- 知识问答/闲聊/无具体业务参数 → {"action":"chat"}

重要：用户消息缺少具体参数时（如只说"帮我算税"但没有商品名/HS编码/目标国），归类为 chat，让 Agent 追问参数。只有用户给出了商品信息或明确说"跳转""去页面操作""自己填"时，才 redirect。
用户输入："""


def _get_intent_llm() -> ChatOpenAI:
    global _intent_llm
    if _intent_llm is None:
        _intent_llm = ChatOpenAI(
            model=settings.llm_model or "qwen-plus",
            temperature=0,
            api_key=settings.llm_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _intent_llm


# Agent 内部跳转映射（仅用户主动要求跳转时触发）
_REDIRECT_MAP = {
    "redirect_classify": {"page": "classify", "label": "HS 归类", "force": False},
    "redirect_tariff": {"page": "tariff", "label": "关税计算", "force": False},
    "redirect_compliance": {"page": "compliance", "label": "合规校验", "force": False},
    "redirect_pipeline": {"page": "pipeline", "label": "一键全流程", "force": True},
    "redirect_dashboard": {"page": "dashboard", "label": "风险看板", "force": False},
}


async def classify_intent(message: str) -> dict:
    """用 LLM 判断用户意图"""
    try:
        llm = _get_intent_llm()
        resp = await llm.ainvoke(INTENT_PROMPT + message)
        text = resp.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception:
        return {"action": "chat"}


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: str | None = Field(default=None)
    skip_redirect: bool = Field(default=False, description="跳过意图分类，直接走 Agent 回答")


class ChatResponse(BaseModel):
    reply: str = ""
    action: str | None = None
    redirect: dict | None = None
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def send_message(req: ChatRequest, user: User = Depends(require_user)):
    """三层路由：skip_redirect → 意图分类 → ReAct Agent"""
    session_id = req.session_id or uuid.uuid4().hex[:12]
    logger.info("chat.message", session_id=session_id, user_id=user.id, skip=req.skip_redirect)

    # 保存用户消息
    async with async_session() as db:
        db.add(ChatMessage(session_id=session_id, user_id=user.id, role="user", content=req.message))
        await db.commit()

    action = None
    redirect = None

    # === 第 0 层：用户拒绝跳转 → 直接走 Agent ===
    if req.skip_redirect:
        reply = (await chat_agent(req.message, session_id))["reply"]

    else:
        # === 第 1 层：意图分类 ===
        intent = await classify_intent(req.message)

        if intent.get("action") == "redirect" and intent.get("page"):
            page = intent["page"]
            label = intent.get("label", page)
            force = intent.get("force", False)
            reply = f'我识别到你想进行{label}，需要跳转到对应页面吗？'
            action = "confirm_redirect"
            redirect = {"page": page, "label": label, "force": force}
        else:
            # === 第 2 层：走 Agent ===
            reply = (await chat_agent(req.message, session_id))["reply"]
            # Agent 对话中用户主动要求跳转 → 直接跳，不弹确认卡片
            for key, info in _REDIRECT_MAP.items():
                tag = f"[ACTION:{key}]"
                if tag in reply:
                    reply = reply.replace(tag, "").strip()
                    action = "redirect"
                    redirect = info
                    break

    # 保存 agent 回复
    async with async_session() as db:
        db.add(ChatMessage(session_id=session_id, user_id=user.id, role="assistant", content=reply))
        await db.commit()

    return ChatResponse(reply=reply, action=action, redirect=redirect, session_id=session_id)
