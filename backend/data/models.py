from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HsCode(Base):
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
    created_at = Column(DateTime, default=_utcnow)


class TariffSchedule(Base):
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
    created_at = Column(DateTime, default=_utcnow)


class SanctionEntry(Base):
    __tablename__ = "sanctions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(300), nullable=False)
    country = Column(String(10), nullable=True)
    list_type = Column(String(50), nullable=False)
    restriction_type = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class Declaration(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, index=True, nullable=False)
    commodity_name = Column(String(500), nullable=False)
    commodity_description = Column(Text, nullable=True)
    hs_code = Column(String(20), nullable=True)
    target_country = Column(String(10), nullable=False)
    results = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
