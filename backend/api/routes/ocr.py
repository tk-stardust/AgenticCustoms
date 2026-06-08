"""图片 OCR 识别接口——上传商品照片自动提取商品信息"""

import base64
import binascii
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.llm import chat_vision
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["ocr"])

OCR_PROMPT = """你是一个外贸商品信息提取助手。根据图片提取以下信息，严格按 JSON 格式返回：

{
  "name": "商品名称（简短，如：蓝牙音箱）",
  "material": "材质（如：塑料、金属）",
  "function": "核心功能（如：音乐播放、语音助手）",
  "usage": "用途（如：家庭娱乐、办公）",
  "description": "详细外观描述（包含颜色、形状、尺寸等视觉特征）"
}

只输出 JSON，不要其他文字。如果某字段无法从图片判断，填空字符串。"""


class OCRRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 编码的图片数据")
    image_type: str = Field(default="image/jpeg", description="图片 MIME 类型")


class OCRResponse(BaseModel):
    name: str = ""
    material: str = ""
    function: str = ""
    usage: str = ""
    description: str = ""


@router.post("/ocr", response_model=OCRResponse)
async def ocr_analyze(req: OCRRequest):
    """上传商品图片，AI 提取商品信息

    :param req: 含 base64 图片和 MIME 类型
    :returns: 提取的商品名称、材质、功能、用途、描述
    """
    # 校验 base64
    try:
        base64.b64decode(req.image_base64)
    except binascii.Error:
        raise HTTPException(400, "无效的 base64 编码")

    logger.info("ocr.start", image_type=req.image_type)
    response = await chat_vision(req.image_base64, req.image_type, OCR_PROMPT)

    # 解析 JSON 响应
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("ocr.parse_failed", raw=response[:200])
        # 解析失败时尝试从原始文本提取
        return OCRResponse(description=response[:500])

    return OCRResponse(**data)
