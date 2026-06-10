"""关税计算接口——支持 AI 自动归类与直接编码两种模式"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from domain.tariff_result import TariffResult
from api.deps import get_hs_agent, get_tariff_agent
from shared.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["tariff"])


class TariffRequest(BaseModel):
    """关税计算请求——hs_code 有值时走直接模式，否则走自动归类模式"""

    hs_code: str | None = Field(default=None, description="已知 HS 编码时填写（直接模式）")
    name: str = Field(default="", description="商品名称（自动归类模式）")
    description: str = Field(default="", description="商品描述")
    material: str = Field(default="", description="材质")
    function: str = Field(default="", description="功能")
    target_country: str = Field(default="US", description="目标国家代码")
    declared_value: float = Field(default=0.0, description="申报价值 (USD)")


class TariffCalcResponse(BaseModel):
    """关税计算响应——包含 HS 归类结果（仅自动模式）与税费明细"""

    hs_code: str
    confidence: float = 0
    hs_description: str = ""
    product_name: str = ""
    tariff: TariffResult


@router.post("/tariff", response_model=TariffCalcResponse)
async def calculate_tariff(
    req: TariffRequest,
    hs_agent=Depends(get_hs_agent),
    tariff_agent=Depends(get_tariff_agent),
):
    """关税计算

    直接模式：传 hs_code → 直接查税率；
    自动归类模式：传 name/description → 先 HS 归类 → 再查税率。
    """
    hs_code = req.hs_code
    confidence = 0.0
    hs_description = ""
    product_name = req.name

    if hs_code:
        logger.info("api.tariff.direct", hs_code=hs_code, country=req.target_country)
    else:
        logger.info("api.tariff.auto", name=req.name, country=req.target_country)
        from domain.commodity import Commodity

        commodity = Commodity(
            name=req.name or "未命名商品",
            description=req.description,
            material=req.material,
            function=req.function,
        )
        hs_result = await hs_agent.run(commodity)
        hs_code = hs_result.code
        confidence = hs_result.confidence
        hs_description = hs_result.description
        product_name = req.name or hs_result.description

    tariff = await tariff_agent.run(
        hs_code=hs_code,
        country=req.target_country,
        declared_value=req.declared_value,
    )

    return TariffCalcResponse(
        hs_code=hs_code,
        confidence=confidence,
        hs_description=hs_description,
        product_name=product_name,
        tariff=tariff,
    )
