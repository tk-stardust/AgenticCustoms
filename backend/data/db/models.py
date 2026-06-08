"""SQLAlchemy ORM 模型——MySQL 表结构定义"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


class HsCode(Base):
    """HS 编码主表——各国海关税则"""
    __tablename__ = "hs_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=False)
    chapter = Column(String(2), nullable=False)
    heading = Column(String(4), nullable=False)
    country = Column(String(10), nullable=False, default="CN")
    base_rate = Column(Float, default=0.0)
    vat_rate = Column(Float, default=0.0)
    unit = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    # server_default 由 MySQL 生成时间，避免 Python 端 UTC/本地时区不一致
    created_at = Column(DateTime, server_default=func.now())


class TariffSchedule(Base):
    """关税税率表——按目标国 + HS 前缀匹配"""
    __tablename__ = "tariff_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    country = Column(String(10), nullable=False)
    hs_code_prefix = Column(String(10), nullable=False)
    base_rate = Column(Float, default=0.0)
    vat_rate = Column(Float, default=0.0)
    anti_dumping_rate = Column(Float, default=0.0)
    preferential_rate = Column(Float, nullable=True)
    fta_name = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SanctionEntry(Base):
    """制裁清单——实体黑名单"""
    __tablename__ = "sanctions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(300), nullable=False)
    country = Column(String(100), nullable=True)
    list_type = Column(String(50), nullable=False)
    restriction_type = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Declaration(Base):
    """申报记录——每次全流程的结果快照"""
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, index=True, nullable=False)
    commodity_name = Column(String(500), nullable=False)
    commodity_description = Column(Text, nullable=True)
    hs_code = Column(String(20), nullable=True)
    target_country = Column(String(10), nullable=False)
    # JSON 列存储完整的流水线结果（HS/关税/合规/原产地/申报文件）
    results = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
