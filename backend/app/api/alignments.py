from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Alignment

router = APIRouter()


@router.get("/")
def list_alignments(
    status: str = Query("pending"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Alignment)
        .filter(Alignment.status == status)
        .order_by(Alignment.today_date.desc())
        .limit(limit)
        .all()
    )
    return rows


@router.patch("/{alignment_id}/status")
def update_status(alignment_id: int, status: str, db: Session = Depends(get_db)):
    row = db.query(Alignment).get(alignment_id)
    if not row:
        return {"error": "not found"}
    row.status = status
    db.commit()
    return {"id": alignment_id, "status": status}
