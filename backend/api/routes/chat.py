"""AI 对话接口 —— 意图分类 + 参数收集 + ReAct Agent + 历史记录"""

import json
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select, delete

from agents.chat.agent import chat as chat_agent, clear_agent_memory
from api.deps import require_user
from data.db.database import async_session
from data.db.models import ChatMessage, User
from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# 意图分类——独立 LLM，temperature=0 保证稳定
_intent_llm: ChatOpenAI | None = None

INTENT_PROMPT = """分析用户消息，输出 JSON（不要其他内容）：

1. 判断意图（intent）：
   - HS归类/查询编码 → classify
   - 关税计算/税率查询 → tariff
   - 合规校验/风险检查/禁限品 → compliance
   - 生成申报文件/下载报告/打印PDF → pipeline（force=true）
   - 查看风险看板/数据统计/图表 → dashboard
   - 知识问答/闲聊/无具体业务参数 → chat

2. 如果 intent 不是 chat，提取商品实体（entities），未提及的字段用 null：
   - name: 商品名称（如"蓝牙耳机""音箱"）
   - description: 商品描述（材质、功能、用途等描述）
   - material: 材质
   - function: 功能
   - country: 目标国家代码（美国→US, 欧盟→EU, 越南→VN）；未提及则 null
   - hs_code: HS编码（如8518.22.00）
   - declared_value: 申报价值数字

输出格式示例：
{"intent":"tariff","label":"关税计算","entities":{"name":"蓝牙音箱","description":null,"material":null,"function":null,"country":"US","hs_code":null,"declared_value":null}}
{"intent":"classify","label":"HS归类","entities":{"name":"蓝牙耳机","description":"无线降噪耳机","material":"塑料","function":"蓝牙连接","country":null,"hs_code":null,"declared_value":null}}
{"intent":"chat","label":"","entities":{}}

规则：
- 用户消息缺少关键业务参数（如"帮我算税"无商品名/HS编码/目标国），intent=chat
- 用户只说了商品名但没表达业务意图（如只说"蓝牙耳机"），intent=chat
- 用户表达了业务意图+至少一个关键实体（商品名或HS编码），才 redirect
- 目标国家不在 US/EU/VN（美国/欧盟/越南）范围内 → intent=chat，让 Agent 告知用户当前仅支持这三个地区
- pipeline 的 force 默认为 true
用户输入："""

# 跳过检测——判断用户是否想跳过参数补充
SKIP_PROMPT = """判断用户是否想跳过参数补充、直接跳转页面。以下情况都算跳过：
- 明确说"跳过""算了""不用了""直接跳转""去页面""我自己填""先跳转""跳转吧""不填了"
- 表达不想继续提供参数
- 表达想直接去功能页面自己操作

只输出 JSON：{"skip": true} 或 {"skip": false}
用户输入："""

# 参数提取——从用户补充消息中提取商品参数
EXTRACT_PARAMS_PROMPT = """从用户消息中提取商品参数。只输出 JSON，不要其他内容：
{"name":"商品名称或null","description":"商品描述或null","material":"材质或null","function":"功能或null","country":"US/EU/VN或null","hs_code":"HS编码或null","declared_value":数字或null}

国家名称映射：美国→US, 欧盟→EU, 越南→VN
用户输入："""

# 各页面参数需求定义
PAGE_PARAMS: dict[str, dict] = {
    "classify": {
        "required": ["name", "description"],
        "optional": ["material", "function", "usage"],
        "label": "HS归类",
    },
    "tariff": {
        "required": ["country"],
        "needs_one_of": [["name", "hs_code"]],  # 商品名或HS编码至少一个
        "optional": ["name", "description", "material", "function", "hs_code", "declared_value"],
        "label": "关税计算",
    },
    "compliance": {
        "required": ["name", "country"],
        "optional": ["description", "material", "function", "hs_code"],
        "label": "合规校验",
    },
    "pipeline": {
        "required": ["name", "description"],
        "optional": ["material", "function", "usage", "declared_value", "hs_code", "country"],
        "label": "一键全流程",
    },
}

# 参数收集会话状态（内存存储，与 MemorySaver 同生命周期）
_param_sessions: dict[str, dict] = {}
MAX_ASK_COUNT = 2


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


def _parse_llm_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text)


async def _llm_json(prompt: str, message: str) -> dict:
    """调用 LLM 返回 JSON 结果"""
    try:
        llm = _get_intent_llm()
        resp = await llm.ainvoke(prompt + message)
        return _parse_llm_json(resp.content.strip())
    except Exception:
        return {}


async def classify_intent(message: str) -> dict:
    """用 LLM 判断用户意图 + 提取商品实体"""
    result = await _llm_json(INTENT_PROMPT, message)
    if not result or "intent" not in result:
        return {"intent": "chat", "label": "", "entities": {}}
    return result


async def detect_skip(message: str) -> bool:
    """检测用户是否想跳过参数补充"""
    result = await _llm_json(SKIP_PROMPT, message)
    return result.get("skip", False)


async def extract_params_from_message(message: str) -> dict:
    """从用户消息中提取商品参数"""
    result = await _llm_json(EXTRACT_PARAMS_PROMPT, message)
    if not result:
        return {}
    # 过滤掉 null 值和非预期字段
    valid_keys = {"name", "description", "material", "function", "country", "hs_code", "declared_value"}
    return {k: v for k, v in result.items() if k in valid_keys and v is not None and v != ""}


def merge_params(existing: dict, new_params: dict) -> dict:
    """合并参数，非 null 的新值覆盖旧值"""
    merged = dict(existing)
    for k, v in new_params.items():
        if v is not None and v != "":
            merged[k] = v
    return merged


def check_params(page: str, params: dict) -> tuple[list[str], bool]:
    """检查参数是否满足页面必填要求。返回 (missing_fields, is_complete)"""
    if page not in PAGE_PARAMS:
        return [], True

    req = PAGE_PARAMS[page]
    missing = []

    for field in req.get("required", []):
        if not params.get(field):
            missing.append(field)

    # 检查 needs_one_of
    for group in req.get("needs_one_of", []):
        if not any(params.get(f) for f in group):
            # 只把第一个作为提示用的缺失项
            missing.append(group[0])

    is_complete = len(missing) == 0
    return missing, is_complete


def _missing_labels(fields: list[str]) -> list[str]:
    """将字段名转为中文标签"""
    labels = {
        "name": "商品名称", "description": "商品描述", "material": "材质",
        "function": "功能", "usage": "用途", "country": "目标国家",
        "hs_code": "HS编码", "declared_value": "申报价值",
    }
    return [labels.get(f, f) for f in fields]


def _params_to_query(params: dict) -> str:
    """将参数字典转为 URL query string"""
    clean = [(k, v) for k, v in params.items() if v is not None and v != ""]
    return urlencode(clean)


def _cancel_collection(session_id: str):
    """清除参数收集状态"""
    _param_sessions.pop(session_id, None)


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: str | None = Field(default=None)
    skip_redirect: bool = Field(default=False, description="跳过意图分类，直接走 Agent 回答")


class ChatResponse(BaseModel):
    reply: str = ""
    action: str | None = None
    redirect: dict | None = None
    session_id: str
    params: dict | None = None       # 已提取的参数
    missing: list[str] | None = None # 缺失的必填字段（中文标签）
    complete: bool = False           # 参数是否齐全，跳转后可自动执行


@router.post("/chat", response_model=ChatResponse)
async def send_message(req: ChatRequest, user: User = Depends(require_user)):
    """多层级路由：参数收集 → skip_redirect → 意图分类 → ReAct Agent"""
    session_id = req.session_id or uuid.uuid4().hex[:12]
    logger.info("chat.message", session_id=session_id, user_id=user.id, skip=req.skip_redirect)

    # 保存用户消息
    async with async_session() as db:
        db.add(ChatMessage(session_id=session_id, user_id=user.id, role="user", content=req.message))
        await db.commit()

    action: str | None = None
    redirect: dict | None = None
    params: dict | None = None
    missing: list[str] | None = None
    complete: bool = False

    # === 第 0 层：用户拒绝跳转 → 清除收集状态，直接走 Agent ===
    if req.skip_redirect:
        _cancel_collection(session_id)
        reply = (await chat_agent(req.message, session_id))["reply"]

    else:
        # === 第 1 层：参数收集中？ ===
        coll = _param_sessions.get(session_id)

        if coll and coll.get("collecting"):
            # 先检测是否想跳过
            if await detect_skip(req.message):
                # 用户跳过 → 用已收集的参数跳转
                collected = coll["collected"]
                page = coll["target_page"]
                missing_fields, is_complete = check_params(page, collected)
                _cancel_collection(session_id)

                reply = "好的，已为您跳转到对应页面。已填写的信息已预填，其余字段可手动补充。"
                action = "confirm_redirect"
                redirect = {
                    "page": page,
                    "label": coll["target_label"],
                    "force": False,
                    "query": _params_to_query(collected),
                }
                params = collected
                missing = _missing_labels(missing_fields)
                complete = is_complete
            else:
                # 尝试提取参数
                new_params = await extract_params_from_message(req.message)
                if new_params:
                    # 合并参数
                    coll["collected"] = merge_params(coll["collected"], new_params)
                    coll["ask_count"] += 1

                # 重新检查完整性
                collected = coll["collected"]
                page = coll["target_page"]
                missing_fields, is_complete = check_params(page, collected)

                if is_complete:
                    # 齐全了 → 跳转
                    _cancel_collection(session_id)
                    reply = "信息已齐全，为您跳转到对应页面并自动查询。"
                    action = "confirm_redirect"
                    redirect = {
                        "page": page,
                        "label": coll["target_label"],
                        "force": False,
                        "query": _params_to_query(collected),
                    }
                    params = collected
                    missing = []
                    complete = True
                elif coll["ask_count"] >= MAX_ASK_COUNT:
                    # 达到追问上限 → 不再追问，直接跳转
                    _cancel_collection(session_id)
                    reply = f"已达到追问上限，为您跳转到对应页面。已填写的字段已预填，其余字段请手动补充。"
                    action = "confirm_redirect"
                    redirect = {
                        "page": page,
                        "label": coll["target_label"],
                        "force": False,
                        "query": _params_to_query(collected),
                    }
                    params = collected
                    missing = _missing_labels(missing_fields)
                    complete = False
                else:
                    # 继续追问
                    missing_labels = _missing_labels(missing_fields)
                    reply = f"还需要补充以下信息：{'、'.join(missing_labels)}。提供完整信息后可直接显示结果。或者回复「跳过」直接前往页面。"
                    action = "ask_params"
                    params = collected
                    missing = missing_labels
                    complete = False

        else:
            # === 第 2 层：意图分类 + 实体提取 ===
            intent = await classify_intent(req.message)

            if intent.get("intent") not in ("", "chat") and intent.get("intent"):
                page = intent["intent"]
                label = intent.get("label", PAGE_PARAMS.get(page, {}).get("label", page))
                force = intent.get("force", page == "pipeline")
                entities = intent.get("entities", {}) or {}

                # 过滤有效实体
                valid_entities = {
                    k: v for k, v in entities.items()
                    if v is not None and v != "" and v != "null"
                }

                # 检查参数完整性
                missing_fields, is_complete = check_params(page, valid_entities)

                if is_complete:
                    # 参数齐全 → 直接跳转确认卡片
                    reply = f"我识别到你想进行{label}。已提取完整信息，跳转后可自动查询。需要跳转吗？"
                    action = "confirm_redirect"
                    redirect = {
                        "page": page,
                        "label": label,
                        "force": force,
                        "query": _params_to_query(valid_entities),
                    }
                    params = valid_entities
                    missing = []
                    complete = True
                else:
                    # 参数不全 → 进入收集模式
                    _param_sessions[session_id] = {
                        "collecting": True,
                        "target_page": page,
                        "target_label": label,
                        "collected": valid_entities,
                        "ask_count": 0,
                    }
                    missing_labels = _missing_labels(missing_fields)
                    reply = (
                        f"我识别到你想进行{label}。"
                        f"已提取：{'、'.join(f'{_missing_labels([k])[0]}「{v}」' for k, v in valid_entities.items())}。\n"
                        f"⚠️ 缺少：{'、'.join(missing_labels)}。请补充，提供完整信息后可直接显示结果。"
                    )
                    action = "ask_params"
                    params = valid_entities
                    missing = missing_labels
                    complete = False
            else:
                # === 第 3 层：走 Agent ===
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

    return ChatResponse(
        reply=reply, action=action, redirect=redirect, session_id=session_id,
        params=params, missing=missing, complete=complete,
    )


@router.get("/chat/history")
async def get_history(session_id: str, user: User = Depends(require_user)):
    """获取当前会话的聊天历史"""
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.asc())
        )
        rows = result.scalars().all()
        return [{"role": r.role, "content": r.content} for r in rows]


@router.delete("/chat/history")
async def delete_history(session_id: str, user: User = Depends(require_user)):
    """清空当前会话的聊天历史（数据库 + Agent 记忆）"""
    async with async_session() as db:
        await db.execute(
            delete(ChatMessage).where(
                ChatMessage.session_id == session_id, ChatMessage.user_id == user.id
            )
        )
        await db.commit()
    clear_agent_memory(session_id)
    _cancel_collection(session_id)
    logger.info("chat.history.cleared", session_id=session_id, user_id=user.id)
    return {"ok": True}
