from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import ComputedLevel

router = APIRouter()


@router.get("/")
def list_levels(limit: int = Query(30, le=200), db: Session = Depends(get_db)):
    rows = (
        db.query(ComputedLevel)
        .order_by(ComputedLevel.trade_date.desc())
        .limit(limit)
        .all()
    )
    return rows
