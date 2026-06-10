"""合规校验接口——检查商品出口合规风险"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from domain.commodity import Commodity
from domain.compliance_result import ComplianceResult
from api.deps import get_hs_agent, require_user
from agents.compliance_checker.agent import ComplianceCheckerAgent
from data.db.models import User
from shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["compliance"])


class ComplianceRequest(BaseModel):
    name: str = Field(..., description="商品名称")
    description: str = Field(default="", description="商品描述")
    material: str = Field(default="", description="材质")
    function: str = Field(default="", description="功能")
    target_country: str = Field(default="US", description="目标国家代码")
    hs_code: str | None = Field(default=None, description="已知 HS 编码可直接填写")


class ComplianceResponse(BaseModel):
    risk_level: str
    violations: list[dict]
    license_required: bool
    license_type: str | None
    sanctions_hit: bool
    summary: str
    hs_code: str


@router.post("/compliance", response_model=ComplianceResponse)
async def check_compliance(
    req: ComplianceRequest,
    user: User = Depends(require_user),
    hs_agent=Depends(get_hs_agent),
):
    """合规校验——检查商品出口到目标国的合规风险"""
    logger.info("api.compliance", name=req.name, country=req.target_country)

    hs_code = req.hs_code
    if not hs_code:
        commodity = Commodity(
            name=req.name,
            description=req.description,
            material=req.material,
            function=req.function,
        )
        hs_result = await hs_agent.run(commodity)
        hs_code = hs_result.code

    agent = ComplianceCheckerAgent()
    commodity = Commodity(
        name=req.name,
        description=req.description,
        material=req.material,
        function=req.function,
    )
    result = await agent.run(commodity=commodity, hs_code=hs_code, country=req.target_country)

    return ComplianceResponse(
        risk_level=result.risk_level,
        violations=[v.model_dump() for v in result.violations],
        license_required=result.license_required,
        license_type=result.license_type,
        sanctions_hit=result.sanctions_hit,
        summary=result.summary,
        hs_code=hs_code,
    )
