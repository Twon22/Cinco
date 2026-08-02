from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.pipeline import run_pipeline, compute_all_levels, scan_all_alignments

router = APIRouter()


@router.post("/run")
def run_full_pipeline(db: Session = Depends(get_db)):
    """Compute levels for every day, then scan for alignments."""
    return run_pipeline(db)


@router.post("/compute-levels")
def compute_levels_only(db: Session = Depends(get_db)):
    """Recompute open ranges and Fibonacci levels for every day."""
    return compute_all_levels(db)


@router.post("/scan-alignments")
def scan_alignments_only(db: Session = Depends(get_db)):
    """Rescan for alignments using existing computed levels."""
    return scan_all_alignments(db)
