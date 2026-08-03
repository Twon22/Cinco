"""
Journey vs. real trade detection.

The framework's central discovery: an alignment flags a day worth WATCHING,
not necessarily a day worth TRADING. Several times, a day that looked like an
independent trade turned out to be the approach into a different day's move.

The tell is exact and mechanical. When a day's price extreme lands precisely on
another day's own open-range boundary, that day was the path, not the trade.

Confirmed cases from the original analysis:
    Jan 22  extreme 5597.84  ==  Jan 29's 0.0    (the real trade was Jan 29)
    Apr 1   extreme 4800.13  ==  Apr 2's 0.0     (the real trade was Apr 2)
    Jun 10  and Jun 12       ->  both converged on Jun 17

This module finds candidates. It does NOT decide — the framework is explicit
that the human confirms on the chart.
"""

import pandas as pd
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import ComputedLevel
from app.services.pipeline import load_bars


# How close the extreme must land to another day's level to count as "landing on it"
LANDING_TOLERANCE = 3.0

# How many trading days forward to look for the destination day
FORWARD_WINDOW = 10

# Journey detection needs a LONGER window than trade measurement.
# A trade is held 3-4 days, but a day can be the approach into a setup that
# only resolves a week later. Jan 22 -> Jan 29 requires a 6-day reach; at the
# 4-day trade cap the connection is invisible.
JOURNEY_HOLD_DAYS = 8


def _levels_by_date(db: Session) -> dict:
    """Map every trading date to its own open-range boundaries."""
    rows = db.query(ComputedLevel).filter(
        ComputedLevel.is_tie.is_(False)
    ).order_by(ComputedLevel.trade_date).all()

    out = {}
    for r in rows:
        if r.level_00 is None or r.level_1 is None:
            continue
        out[r.trade_date] = {
            "0.0": float(r.level_00),
            "1": float(r.level_1),
        }
    return out


def find_journey_candidates(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    hold_days: int = JOURNEY_HOLD_DAYS,
) -> dict:
    """
    For every day with computed levels, measure where its move ran to,
    then check whether that extreme lands on a LATER day's own boundary.

    A hit means the earlier day was likely the approach into the later day's
    setup, rather than an independent trade of its own.
    """
    df = load_bars(db)
    if df.empty:
        return {"error": "No bars in database."}

    levels = _levels_by_date(db)
    if not levels:
        return {"error": "No computed levels. Run the pipeline first."}

    all_dates = sorted(levels.keys())
    if start_date:
        all_dates = [d for d in all_dates if d >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d <= end_date]

    date_index = {d: i for i, d in enumerate(sorted(levels.keys()))}
    ordered = sorted(levels.keys())

    candidates = []

    for d in all_dates:
        day_levels = levels[d]
        hi = max(day_levels["0.0"], day_levels["1"])
        lo = min(day_levels["0.0"], day_levels["1"])

        # Find the first bar that CLOSES outside the day's own range
        day_bars = df[df["bar_date"] == d].reset_index(drop=True)
        if day_bars.empty:
            continue

        break_idx = None
        direction = None
        for idx, bar in day_bars.iterrows():
            if bar["close"] > hi:
                break_idx, direction = idx, "up"
                break
            if bar["close"] < lo:
                break_idx, direction = idx, "down"
                break

        if break_idx is None:
            continue

        # Track the move forward over the hold window
        forward = df[df["bar_date"] >= d].reset_index(drop=True)
        window_dates = sorted(forward["bar_date"].unique())[:hold_days]
        window = forward[forward["bar_date"].isin(window_dates)]
        window = window.iloc[break_idx:].reset_index(drop=True)

        if window.empty:
            continue

        if direction == "up":
            extreme = float(window["high"].max())
            extreme_row = window.loc[window["high"].idxmax()]
        else:
            extreme = float(window["low"].min())
            extreme_row = window.loc[window["low"].idxmin()]

        # Does that extreme land on a LATER day's own boundary?
        i = date_index.get(d)
        if i is None:
            continue

        for later in ordered[i + 1: i + 1 + FORWARD_WINDOW]:
            for label, price in levels[later].items():
                diff = abs(extreme - price)
                if diff <= LANDING_TOLERANCE:
                    candidates.append({
                        "journey_date": str(d),
                        "direction": direction,
                        "break_bar": str(day_bars.iloc[break_idx]["bar_time"]),
                        "extreme": round(extreme, 2),
                        "extreme_date": str(extreme_row["bar_date"]),
                        "destination_date": str(later),
                        "destination_level": label,
                        "destination_price": round(price, 2),
                        "diff": round(diff, 2),
                        "trading_days_ahead": ordered.index(later) - i,
                    })

    # Tightest matches first — those are the most convincing
    candidates.sort(key=lambda c: c["diff"])

    return {
        "candidates": candidates,
        "count": len(candidates),
        "tolerance": LANDING_TOLERANCE,
        "note": (
            "Each row is a day whose move ran into a later day's own open-range "
            "boundary. That pattern suggests the earlier day was the approach, "
            "not an independent trade. Confirm on the chart before acting on it."
        ),
    }


def check_one_day(db: Session, trade_date: date, hold_days: int = JOURNEY_HOLD_DAYS) -> dict:
    """Run the journey check for a single day."""
    result = find_journey_candidates(
        db, start_date=trade_date, end_date=trade_date, hold_days=hold_days
    )
    if "error" in result:
        return result

    hits = result["candidates"]
    return {
        "trade_date": str(trade_date),
        "is_journey_candidate": len(hits) > 0,
        "matches": hits,
        "interpretation": (
            f"This day's move ran into {len(hits)} later day's level(s). "
            "It may be the approach into that day rather than a trade of its own."
            if hits else
            "This day's move did not land on any later day's boundary. "
            "No evidence it was a journey day."
        ),
    }
