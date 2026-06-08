"""HS 编码归类接口"""

from fastapi import APIRouter, Depends

from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from api.deps import get_hs_agent
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["classify"])


@router.post("/classify", response_model=HsCodeResult)
async def classify(commodity: Commodity, agent=Depends(get_hs_agent)):
    """HS 编码归类——输入商品描述，返回 HS 编码、置信度、推理路径和条文溯源

    :param commodity: 商品实体（名称、描述、材质、功能、用途）
    :param agent: 依赖注入的 HS 归类智能体
    """
    logger.info("api.classify.request", name=commodity.name)
    result = await agent.run(commodity)
    return result
