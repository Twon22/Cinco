"""
Cinco pipeline.

Connects raw H1 bars to the computation engine and persists results:

    daily_bars  →  compute_levels   →  computed_levels
                →  scan_alignments  →  alignments

Designed to be re-runnable: recomputing a day overwrites its previous
result rather than creating duplicates.
"""

import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.models import DailyBar, ComputedLevel, Alignment
from app.services.engine import (
    compute_levels,
    scan_alignments,
    DayLevels,
    BOUNDARY_LOOKBACK_DAYS,
)


# ---------------------------------------------------------------------------
# Loading bars out of the database
# ---------------------------------------------------------------------------

def load_bars(db: Session) -> pd.DataFrame:
    """Pull every bar into a DataFrame, sorted chronologically."""
    rows = db.execute(
        select(
            DailyBar.bar_date,
            DailyBar.bar_time,
            DailyBar.open,
            DailyBar.high,
            DailyBar.low,
            DailyBar.close,
        ).order_by(DailyBar.bar_date, DailyBar.bar_time)
    ).all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["bar_date", "bar_time", "open", "high", "low", "close"])
    # DECIMAL columns come back as Decimal objects; convert for arithmetic
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# Step 1 — compute levels for every day
# ---------------------------------------------------------------------------

def compute_all_levels(db: Session) -> dict:
    """
    Compute open range and Fibonacci levels for every trading day
    that has enough bars. Returns a summary dict.
    """
    df = load_bars(db)
    if df.empty:
        return {"computed": 0, "skipped": 0, "ties": 0, "gaps": 0,
                "errors": [], "message": "No bars in database."}

    trading_days = sorted(df["bar_date"].unique())

    computed = 0
    skipped = 0
    ties = 0
    gaps = 0
    errors = []

    prior_close = None
    prior_bar = None

    for d in trading_days:
        day_bars = df[df["bar_date"] == d].reset_index(drop=True)

        # Need at least 3 bars to form an open range
        if len(day_bars) < 3:
            skipped += 1
            # Still update the carry-forward values for the next day
            last = day_bars.iloc[-1] if len(day_bars) else None
            if last is not None:
                prior_close = float(last["close"])
                prior_bar = {"high": float(last["high"]), "low": float(last["low"])}
            continue

        try:
            levels = compute_levels(
                day_bars,
                prior_close=prior_close,
                prior_bar=prior_bar,
            )
        except ValueError as e:
            # Gap detected but no prior bar available (first day in the file)
            errors.append(str(e))
            skipped += 1
            last = day_bars.iloc[-1]
            prior_close = float(last["close"])
            prior_bar = {"high": float(last["high"]), "low": float(last["low"])}
            continue

        _upsert_level(db, levels)
        computed += 1
        if levels.is_tie:
            ties += 1
        if levels.is_gap:
            gaps += 1

        last = day_bars.iloc[-1]
        prior_close = float(last["close"])
        prior_bar = {"high": float(last["high"]), "low": float(last["low"])}

    db.commit()

    return {
        "computed": computed,
        "skipped": skipped,
        "ties": ties,
        "gaps": gaps,
        "errors": errors[:10],
        "total_days": len(trading_days),
    }


def _upsert_level(db: Session, levels: DayLevels) -> None:
    """Insert or update one day's computed levels."""
    existing = db.query(ComputedLevel).filter(
        ComputedLevel.trade_date == levels.trade_date
    ).first()

    values = dict(
        level_00=levels.level_00,
        level_1=levels.level_1,
        level_5_hi=levels.level_5_hi,
        level_x_hi=levels.level_x_hi,
        level_5_lo=levels.level_5_lo,
        level_x_lo=levels.level_x_lo,
        is_tie=levels.is_tie,
        is_gap=levels.is_gap,
    )

    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
    else:
        db.add(ComputedLevel(trade_date=levels.trade_date, **values))


# ---------------------------------------------------------------------------
# Step 2 — scan every day for alignments
# ---------------------------------------------------------------------------

def _row_to_daylevels(row: ComputedLevel) -> DayLevels:
    """Convert a database row back into the engine's DayLevels shape."""
    def f(v):
        return float(v) if v is not None else None

    return DayLevels(
        trade_date=row.trade_date,
        level_00=f(row.level_00),
        level_1=f(row.level_1),
        level_5_hi=f(row.level_5_hi),
        level_x_hi=f(row.level_x_hi),
        level_5_lo=f(row.level_5_lo),
        level_x_lo=f(row.level_x_lo),
        is_tie=bool(row.is_tie),
        is_gap=bool(row.is_gap),
    )


def scan_all_alignments(db: Session, preserve_reviewed: bool = True) -> dict:
    """
    Run the alignment scanner across every computed day.

    preserve_reviewed: if True, alignments already marked 'reviewed' or
    'removed' are left alone so a rescan doesn't wipe out your work.
    """
    rows = (
        db.query(ComputedLevel)
        .order_by(ComputedLevel.trade_date)
        .all()
    )

    if not rows:
        return {"days_scanned": 0, "matches_found": 0, "message": "No computed levels."}

    days = [_row_to_daylevels(r) for r in rows]

    # Clear out old pending alignments so a rescan doesn't accumulate stale rows
    if preserve_reviewed:
        db.execute(delete(Alignment).where(Alignment.status == "pending"))
    else:
        db.execute(delete(Alignment))
    db.commit()

    # Keep track of what's already in the table so we don't violate the
    # unique constraint on (today, prior, today_level, prior_level)
    kept = {
        (a.today_date, a.prior_date, a.today_level, a.prior_level)
        for a in db.query(Alignment).all()
    }

    total_matches = 0
    x_to_x = 0
    x_to_boundary = 0

    for i, today in enumerate(days):
        if i == 0:
            continue

        # History is most-recent-first, capped at the boundary lookback
        start = max(0, i - BOUNDARY_LOOKBACK_DAYS)
        history = list(reversed(days[start:i]))

        matches = scan_alignments(today, history)

        for m in matches:
            key = (m.today_date, m.prior_date, m.today_level, m.prior_level)
            if key in kept:
                continue
            kept.add(key)

            db.add(Alignment(
                today_date=m.today_date,
                prior_date=m.prior_date,
                today_level=m.today_level,
                prior_level=m.prior_level,
                today_price=m.today_price,
                prior_price=m.prior_price,
                diff=m.diff,
                match_type=m.match_type,
                is_boundary_day=m.is_boundary_day,
                status="pending",
            ))
            total_matches += 1
            if m.match_type == "x==x":
                x_to_x += 1
            else:
                x_to_boundary += 1

    db.commit()

    return {
        "days_scanned": len(days),
        "matches_found": total_matches,
        "x_to_x": x_to_x,
        "x_to_boundary": x_to_boundary,
    }


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline(db: Session) -> dict:
    """Compute levels for all days, then scan for alignments."""
    levels_result = compute_all_levels(db)
    scan_result = scan_all_alignments(db)
    return {"levels": levels_result, "alignments": scan_result}
