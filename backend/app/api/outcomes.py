from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, time
from app.core.database import get_db
from app.services.outcomes import compute_outcome, compare_holds, suggest_break_bar
from app.models.models import ComputedLevel

router = APIRouter()


@router.get("/compute")
def compute(
    entry_date: date = Query(..., description="e.g. 2026-03-18"),
    entry_time: time = Query(..., description="e.g. 04:00"),
    entry_price: float = Query(...),
    direction: str = Query(..., description="'buy' or 'sell'"),
    hold_days: int = Query(4, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Suggest pips and hold duration for one entry."""
    return compute_outcome(db, entry_date, entry_time, entry_price, direction, hold_days)


@router.get("/compare-holds")
def compare(
    entry_date: date = Query(...),
    entry_time: time = Query(...),
    entry_price: float = Query(...),
    direction: str = Query(...),
    db: Session = Depends(get_db),
):
    """Compute both the 3-day and 4-day outcome side by side."""
    return compare_holds(db, entry_date, entry_time, entry_price, direction)


@router.get("/break-bar/{trade_date}")
def break_bar(trade_date: date, db: Session = Depends(get_db)):
    """
    Find the first bar that closes outside that day's own open range,
    using the levels already computed for the day.
    """
    row = db.query(ComputedLevel).filter(
        ComputedLevel.trade_date == trade_date
    ).first()

    if not row:
        return {"error": f"No computed levels for {trade_date}. Run the pipeline first."}
    if row.is_tie:
        return {"error": f"{trade_date} is a tie day — open range is ambiguous."}
    if row.level_00 is None or row.level_1 is None:
        return {"error": f"{trade_date} has no open range levels."}

    return suggest_break_bar(db, trade_date, float(row.level_00), float(row.level_1))
