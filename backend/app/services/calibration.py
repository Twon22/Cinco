"""
Calibration sweep.

Runs the alignment scanner repeatedly over the same computed levels using
different parameter settings, so the effect of each parameter can be seen
rather than assumed.

Nothing here writes to the alignments table — it only reports counts.
"""

from sqlalchemy.orm import Session
from app.models.models import ComputedLevel
from app.services.engine import ScanConfig, scan_alignments
from app.services.pipeline import _row_to_daylevels


def _run_one(days, config: ScanConfig) -> dict:
    """Scan every day under one config and summarise the result."""
    total = 0
    x_to_x = 0
    x_to_boundary = 0
    days_with_match = set()
    reach_short = 0      # within the intraday window
    reach_long = 0       # only reachable via the boundary rule

    for i, today in enumerate(days):
        if i == 0:
            continue
        start = max(0, i - config.boundary_lookback)
        history = list(reversed(days[start:i]))

        matches = scan_alignments(today, history, config=config)
        if matches:
            days_with_match.add(today.trade_date)

        for m in matches:
            total += 1
            if m.match_type == "x==x":
                x_to_x += 1
            else:
                x_to_boundary += 1
            if m.trading_days_back <= config.intraday_window:
                reach_short += 1
            else:
                reach_long += 1

    scannable = len([d for d in days if not d.is_tie and d.level_x_hi is not None])

    return {
        "tolerance": config.tolerance,
        "intraday_window": config.intraday_window,
        "boundary_lookback": config.boundary_lookback,
        "total_matches": total,
        "x_to_x": x_to_x,
        "x_to_boundary": x_to_boundary,
        "days_with_match": len(days_with_match),
        "scannable_days": scannable,
        "pct_days_flagged": round(100 * len(days_with_match) / scannable, 1) if scannable else 0,
        "from_short_window": reach_short,
        "from_boundary_rule": reach_long,
    }


def sweep_boundary_lookback(
    db: Session,
    values: list[int] = None,
) -> dict:
    """
    Hold everything else fixed and vary only the boundary lookback.

    This is the parameter set from a single confirmed example, so it is
    the one most worth testing.
    """
    values = values or [0, 15, 30, 45, 65, 90, 120]

    rows = db.query(ComputedLevel).order_by(ComputedLevel.trade_date).all()
    if not rows:
        return {"error": "No computed levels. Run the pipeline first."}

    days = [_row_to_daylevels(r) for r in rows]

    results = []
    for v in values:
        cfg = ScanConfig(boundary_lookback=v)
        results.append(_run_one(days, cfg))

    return {
        "parameter": "boundary_lookback",
        "note": (
            "A lookback of 0 disables the boundary rule entirely, leaving only "
            "the short window. Compare how much of the total each setting adds."
        ),
        "results": results,
    }


def sweep_tolerance(
    db: Session,
    values: list[float] = None,
) -> dict:
    """Vary the price-proximity tolerance, holding windows fixed."""
    values = values or [1.0, 2.0, 3.0, 5.0]

    rows = db.query(ComputedLevel).order_by(ComputedLevel.trade_date).all()
    if not rows:
        return {"error": "No computed levels. Run the pipeline first."}

    days = [_row_to_daylevels(r) for r in rows]

    results = [_run_one(days, ScanConfig(tolerance=v)) for v in values]

    return {"parameter": "tolerance", "results": results}


def sweep_intraday_window(
    db: Session,
    values: list[int] = None,
) -> dict:
    """Vary the short lookback window, holding everything else fixed."""
    values = values or [1, 3, 5, 7, 10]

    rows = db.query(ComputedLevel).order_by(ComputedLevel.trade_date).all()
    if not rows:
        return {"error": "No computed levels. Run the pipeline first."}

    days = [_row_to_daylevels(r) for r in rows]

    results = [_run_one(days, ScanConfig(intraday_window=v)) for v in values]

    return {"parameter": "intraday_window", "results": results}
