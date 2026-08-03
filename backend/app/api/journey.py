from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.core.database import get_db
from app.services.journey import (
    find_journey_candidates,
    check_one_day,
    JOURNEY_HOLD_DAYS,
)

router = APIRouter()


@router.get("/candidates")
def candidates(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    hold_days: int = Query(JOURNEY_HOLD_DAYS, ge=2, le=20),
    db: Session = Depends(get_db),
):
    """
    Find days whose move ran into a LATER day's own open-range boundary,
    suggesting they were the approach rather than an independent trade.
    """
    return find_journey_candidates(db, start_date, end_date, hold_days)


@router.get("/check/{trade_date}")
def check(
    trade_date: date,
    hold_days: int = Query(JOURNEY_HOLD_DAYS, ge=2, le=20),
    db: Session = Depends(get_db),
):
    """Run the journey check for a single day."""
    return check_one_day(db, trade_date, hold_days)
