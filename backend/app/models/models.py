from datetime import date, time, datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    Enum, ForeignKey, String, Text, Time, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import DECIMAL, TINYINT
from app.core.database import Base


class DailyBar(Base):
    __tablename__ = "daily_bars"

    id       = Column(BigInteger, primary_key=True, autoincrement=True)
    bar_date = Column(Date, nullable=False)
    bar_time = Column(Time, nullable=False)
    open     = Column(DECIMAL(10, 2), nullable=False)
    high     = Column(DECIMAL(10, 2), nullable=False)
    low      = Column(DECIMAL(10, 2), nullable=False)
    close    = Column(DECIMAL(10, 2), nullable=False)
    volume   = Column(BigInteger)

    __table_args__ = (UniqueConstraint("bar_date", "bar_time", name="uq_bar"),)


class ComputedLevel(Base):
    __tablename__ = "computed_levels"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    trade_date  = Column(Date, nullable=False, unique=True)
    level_00    = Column(DECIMAL(10, 2))
    level_1     = Column(DECIMAL(10, 2))
    level_5_hi  = Column(DECIMAL(10, 2))
    level_x_hi  = Column(DECIMAL(10, 2))
    level_5_lo  = Column(DECIMAL(10, 2))
    level_x_lo  = Column(DECIMAL(10, 2))
    is_tie      = Column(Boolean, default=False)
    is_gap      = Column(Boolean, default=False)
    is_nested   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    alignments_as_today = relationship("Alignment", foreign_keys="Alignment.today_date",
                                       primaryjoin="ComputedLevel.trade_date == Alignment.today_date",
                                       viewonly=True)


class Alignment(Base):
    __tablename__ = "alignments"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    today_date      = Column(Date, nullable=False)
    prior_date      = Column(Date, nullable=False)
    today_level     = Column(String(10), nullable=False)
    prior_level     = Column(String(10), nullable=False)
    today_price     = Column(DECIMAL(10, 2), nullable=False)
    prior_price     = Column(DECIMAL(10, 2), nullable=False)
    diff            = Column(DECIMAL(8, 2), nullable=False)
    match_type      = Column(String(20), nullable=False)
    is_boundary_day = Column(Boolean, default=False)
    status          = Column(Enum("pending", "reviewed", "removed"), default="pending")
    created_at      = Column(DateTime, default=datetime.utcnow)

    trade = relationship("VerifiedTrade", back_populates="alignment", uselist=False)

    __table_args__ = (
        UniqueConstraint("today_date", "prior_date", "today_level", "prior_level",
                         name="uq_alignment"),
    )


class VerifiedTrade(Base):
    __tablename__ = "verified_trades"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    alignment_id = Column(BigInteger, ForeignKey("alignments.id"))
    trade_date   = Column(Date, nullable=False)
    entry_time   = Column(Time, nullable=False)
    entry_price  = Column(DECIMAL(10, 2), nullable=False)
    direction    = Column(Enum("buy", "sell"), nullable=False)
    sr_reference = Column(String(100))
    entry_type   = Column(Enum("immediate", "watch_forward"), nullable=False)
    pips_3day    = Column(DECIMAL(10, 2))
    pips_4day    = Column(DECIMAL(10, 2))
    hold_days    = Column(TINYINT)
    notes        = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)

    alignment = relationship("Alignment", back_populates="trade")
