from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import Optional
from app.core.database import get_db
from app.models.models import Alignment

router = APIRouter()


@router.get("/")
def list_alignments(
    status: Optional[str] = Query("pending"),
    match_type: Optional[str] = Query(None, description="'x==x' or 'x==boundary'"),
    start_date: Optional[date] = Query(None, description="Only alignments on/after this date"),
    end_date: Optional[date] = Query(None, description="Only alignments on/before this date"),
    boundary_only: bool = Query(False, description="Only month-boundary alignments"),
    limit: int = Query(2000, le=10000),
    db: Session = Depends(get_db),
):
    q = db.query(Alignment)

    if status and status != "all":
        q = q.filter(Alignment.status == status)
    if match_type:
        q = q.filter(Alignment.match_type == match_type)
    if start_date:
        q = q.filter(Alignment.today_date >= start_date)
    if end_date:
        q = q.filter(Alignment.today_date <= end_date)
    if boundary_only:
        q = q.filter(Alignment.is_boundary_day.is_(True))

    return q.order_by(Alignment.today_date.desc()).limit(limit).all()


@router.get("/date-range")
def get_date_range(db: Session = Depends(get_db)):
    """
    Returns the earliest and latest alignment dates available,
    so the UI can set sensible default bounds on its date pickers.
    """
    result = db.query(
        func.min(Alignment.today_date),
        func.max(Alignment.today_date),
        func.count(Alignment.id),
    ).one()

    return {
        "min_date": result[0],
        "max_date": result[1],
        "total": result[2],
    }


@router.patch("/{alignment_id}/status")
def update_status(alignment_id: int, status: str, db: Session = Depends(get_db)):
    row = db.query(Alignment).get(alignment_id)
    if not row:
        return {"error": "not found"}
    row.status = status
    db.commit()
    return {"id": alignment_id, "status": status}
