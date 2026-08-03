from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.setup import levels_in_play

router = APIRouter()


@router.get("/levels-in-play")
def in_play(
    lookback_days: int = Query(60, ge=5, le=365),
    max_distance_pips: float = Query(4000, ge=100, le=50000),
    include_5: bool = Query(False, description="Include 5 / 5$ levels"),
    reference_price: Optional[float] = Query(
        None, description="Defaults to the latest close in the database"
    ),
    db: Session = Depends(get_db),
):
    """
    Established SR levels above and below current price — the ones price could
    travel to and react at. Not today's own range boundaries.
    """
    return levels_in_play(
        db, lookback_days, max_distance_pips, include_5, reference_price
    )
