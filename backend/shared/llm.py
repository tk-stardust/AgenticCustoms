"""LLM 调用适配器——封装 DashScope Qwen-Plus 的 OpenAI 兼容接口"""

import asyncio

import httpx

from shared.config import settings
from shared.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 2


async def _chat_once(
    client: httpx.AsyncClient,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    model: str,
) -> str:
    resp = await client.post(
        f"{settings.llm_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    resp.raise_for_status()
    body = resp.json()
    return body["choices"][0]["message"]["content"]


async def chat(
    messages: list[dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 1024,
    model: str | None = None,
) -> str:
    """向 LLM 发送对话请求，失败自动重试最多 {MAX_RETRIES} 次

    :param messages: OpenAI 格式的消息列表 [{"role": "user", "content": "..."}]
    :param temperature: 生成随机性，0.0=确定性输出，归类和合规场景建议 0.1
    :param max_tokens: 回复最大 token 数
    :param model: 模型名，默认取配置 llm_model
    """
    model = model or settings.llm_model
    last_error: str | None = None

    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        for attempt in range(1 + MAX_RETRIES):
            try:
                return await _chat_once(client, messages, temperature, max_tokens, model)
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt  # 1s → 2s 退避
                    logger.warning("llm.retry", attempt=attempt + 1, wait=wait, error=last_error[:120])
                    await asyncio.sleep(wait)
                else:
                    logger.error("llm.exhausted", attempts=attempt + 1, error=last_error[:200])

    raise RuntimeError(f"LLM 调用失败（重试 {MAX_RETRIES} 次后仍失败）：{last_error}")


async def chat_vision(
    image_base64: str,
    image_type: str,
    prompt: str,
    max_tokens: int = 512,
) -> str:
    """向 Qwen-VL-Plus 发送图文请求，失败自动重试

    :param image_base64: 图片 base64 编码（不含 data:xxx;base64, 前缀）
    :param image_type: 图片 MIME 类型，如 image/jpeg、image/png
    :param prompt: 文字提示
    :param max_tokens: 回复最大 token 数
    """
    last_error: str | None = None
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        for attempt in range(1 + MAX_RETRIES):
            try:
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
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    logger.warning("llm_vision.retry", attempt=attempt + 1, wait=wait, error=last_error[:120])
                    await asyncio.sleep(wait)
                else:
                    logger.error("llm_vision.exhausted", attempts=attempt + 1, error=last_error[:200])

    raise RuntimeError(f"视觉模型调用失败（重试 {MAX_RETRIES} 次后仍失败）：{last_error}")
