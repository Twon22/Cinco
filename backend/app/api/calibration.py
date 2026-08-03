from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.calibration import (
    sweep_boundary_lookback,
    sweep_tolerance,
    sweep_intraday_window,
)

router = APIRouter()


@router.get("/boundary-lookback")
def boundary_sweep(
    values: Optional[str] = Query(
        None, description="Comma-separated trading-day values, e.g. '0,30,65,90'"
    ),
    db: Session = Depends(get_db),
):
    parsed = [int(v.strip()) for v in values.split(",")] if values else None
    return sweep_boundary_lookback(db, parsed)


@router.get("/tolerance")
def tolerance_sweep(
    values: Optional[str] = Query(None, description="e.g. '1,2,3,5'"),
    db: Session = Depends(get_db),
):
    parsed = [float(v.strip()) for v in values.split(",")] if values else None
    return sweep_tolerance(db, parsed)


@router.get("/intraday-window")
def intraday_sweep(
    values: Optional[str] = Query(None, description="e.g. '1,3,5,7,10'"),
    db: Session = Depends(get_db),
):
    parsed = [int(v.strip()) for v in values.split(",")] if values else None
    return sweep_intraday_window(db, parsed)
