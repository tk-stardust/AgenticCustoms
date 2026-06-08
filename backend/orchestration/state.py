"""流水线全局状态——贯穿 HS → 并行三 Agent → 文件生成 全流程"""

from typing import TypedDict

from domain.commodity import Commodity
from domain.hs_code import HsCodeResult
from domain.tariff_result import TariffResult
from domain.compliance_result import ComplianceResult
from domain.origin_result import OriginResult
from domain.declaration_doc import DeclarationDoc


class PipelineState(TypedDict, total=False):
    """LangGraph 共享状态，各节点读取输入、写入结果"""

    commodity: Commodity
    target_country: str
    hs_result: HsCodeResult
    tariff_result: TariffResult
    compliance_result: ComplianceResult
    origin_result: OriginResult
    documents: DeclarationDoc
