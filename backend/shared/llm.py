"""LLM 调用适配器——封装 DashScope Qwen-Plus 的 OpenAI 兼容接口"""

import httpx

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)


async def chat(
    messages: list[dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """向 Qwen-Plus 发送对话请求，返回模型回复文本

    :param messages: OpenAI 格式的消息列表 [{"role": "user", "content": "..."}]
    :param temperature: 生成随机性，0.0=确定性输出，归类和合规场景建议 0.1
    :param max_tokens: 回复最大 token 数
    """
    # 直接用 httpx 而非 openai SDK，避免引入额外依赖
    # trust_env=False 防止读取系统 HTTP_PROXY 代理导致连接失败
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        return body["choices"][0]["message"]["content"]


async def chat_vision(
    image_base64: str,
    image_type: str,
    prompt: str,
    max_tokens: int = 512,
) -> str:
    """向 Qwen-VL-Plus 发送图文请求，返回模型回复文本

    :param image_base64: 图片 base64 编码（不含 data:xxx;base64, 前缀）
    :param image_type: 图片 MIME 类型，如 image/jpeg、image/png
    :param prompt: 文字提示
    :param max_tokens: 回复最大 token 数
    """
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": "qwen-vl-plus",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{image_base64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }],
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        return body["choices"][0]["message"]["content"]
