from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, time
from typing import Optional
from app.core.database import get_db
from app.models.models import VerifiedTrade

router = APIRouter()


class TradeIn(BaseModel):
    alignment_id: Optional[int] = None
    trade_date: date
    entry_time: time
    entry_price: float
    direction: str          # 'buy' or 'sell'
    sr_reference: Optional[str] = None
    entry_type: str         # 'immediate' or 'watch_forward'
    pips_3day: Optional[float] = None
    pips_4day: Optional[float] = None
    hold_days: Optional[int] = None
    notes: Optional[str] = None


@router.get("/")
def list_trades(db: Session = Depends(get_db)):
    return db.query(VerifiedTrade).order_by(VerifiedTrade.trade_date.desc()).all()


@router.post("/")
def create_trade(trade: TradeIn, db: Session = Depends(get_db)):
    row = VerifiedTrade(**trade.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
