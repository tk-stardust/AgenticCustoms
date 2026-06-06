from enum import StrEnum


class RiskLevel(StrEnum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class TradeRoute(StrEnum):
    CN_US = "cn_us"
    CN_EU = "cn_eu"
    CN_ASEAN = "cn_asean"


class IntentType(StrEnum):
    HS_CLASSIFY = "hs_classify"
    TARIFF_CALC = "tariff_calc"
    COMPLIANCE_CHECK = "compliance_check"
    ORIGIN_MATCH = "origin_match"
    FULL_PIPELINE = "full_pipeline"
