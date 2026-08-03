"""
Outcome calculation.

Given an entry (date, time, price, direction), measures how far price ran
in that direction before the hold window closed.

Rules, per the validated framework:
  - pips  = raw price difference x 10   (gold convention: 1 pip = $0.10)
  - hold  = count of DISTINCT trading dates involved, counted inclusively
  - the move is measured to its favourable extreme within the window
  - a move that closes back through the entry price is treated as invalidated

This SUGGESTS a number. The framework is explicit that identifying the real
entry is skill-assisted, so the human confirms or overrides.
"""

import pandas as pd
from datetime import date, time
from typing import Optional
from sqlalchemy.orm import Session

from app.services.pipeline import load_bars


PIP_MULTIPLIER = 10.0


def _bars_from_entry(df: pd.DataFrame, entry_date: date, entry_time: time) -> pd.DataFrame:
    """Every bar at or after the entry moment, chronologically."""
    mask = (
        (df["bar_date"] > entry_date)
        | ((df["bar_date"] == entry_date) & (df["bar_time"] >= entry_time))
    )
    return df[mask].reset_index(drop=True)


def compute_outcome(
    db: Session,
    entry_date: date,
    entry_time: time,
    entry_price: float,
    direction: str,
    hold_days: int = 4,
) -> dict:
    """
    Measure the outcome of one entry over a capped hold.

    hold_days counts DISTINCT trading dates inclusive of the entry date,
    so hold_days=4 means the entry day plus the next three trading days.
    """
    if direction not in ("buy", "sell"):
        return {"error": "direction must be 'buy' or 'sell'"}

    df = load_bars(db)
    if df.empty:
        return {"error": "No bars in database."}

    forward = _bars_from_entry(df, entry_date, entry_time)
    if forward.empty:
        return {"error": f"No bars found at or after {entry_date} {entry_time}."}

    # Restrict to the allowed window of distinct trading dates
    distinct_dates = sorted(forward["bar_date"].unique())[:hold_days]
    window = forward[forward["bar_date"].isin(distinct_dates)].reset_index(drop=True)

    if window.empty:
        return {"error": "No bars within the hold window."}

    invalidated_at = None
    extreme = entry_price
    extreme_row = None

    for _, bar in window.iterrows():
        if direction == "buy":
            if bar["high"] > extreme:
                extreme = float(bar["high"])
                extreme_row = bar
            # Invalidation: a close back below the entry price
            if invalidated_at is None and bar["close"] < entry_price:
                invalidated_at = bar
        else:
            if bar["low"] < extreme:
                extreme = float(bar["low"])
                extreme_row = bar
            if invalidated_at is None and bar["close"] > entry_price:
                invalidated_at = bar

    raw_move = (extreme - entry_price) if direction == "buy" else (entry_price - extreme)
    pips = round(raw_move * PIP_MULTIPLIER, 1)

    if extreme_row is not None:
        extreme_date = extreme_row["bar_date"]
        extreme_time = str(extreme_row["bar_time"])
        # Hold = distinct trading dates from entry through the extreme, inclusive
        dates_involved = [d for d in distinct_dates if d <= extreme_date]
        actual_hold = len(dates_involved)
    else:
        extreme_date = entry_date
        extreme_time = str(entry_time)
        actual_hold = 1

    return {
        "entry": {
            "date": str(entry_date),
            "time": str(entry_time),
            "price": entry_price,
            "direction": direction,
        },
        "extreme": {
            "price": round(extreme, 2),
            "date": str(extreme_date),
            "time": extreme_time,
        },
        "raw_move": round(raw_move, 2),
        "pips": pips,
        "hold_days": actual_hold,
        "window_days": len(distinct_dates),
        "invalidated": invalidated_at is not None,
        "invalidated_at": (
            f"{invalidated_at['bar_date']} {invalidated_at['bar_time']}"
            if invalidated_at is not None else None
        ),
        "note": (
            "Suggested figure computed from bar data. Confirm against the chart "
            "before logging — identifying the real entry is skill-assisted."
        ),
    }


def compare_holds(
    db: Session,
    entry_date: date,
    entry_time: time,
    entry_price: float,
    direction: str,
) -> dict:
    """
    Compute the outcome at both 3-day and 4-day holds.

    These can differ substantially — the framework found cases where a
    further leg developed on the fourth day.
    """
    return {
        "hold_3day": compute_outcome(db, entry_date, entry_time, entry_price, direction, 3),
        "hold_4day": compute_outcome(db, entry_date, entry_time, entry_price, direction, 4),
    }


def suggest_break_bar(
    db: Session,
    trade_date: date,
    level_00: float,
    level_1: float,
) -> dict:
    """
    Find the first bar that CLOSES outside the day's own open range.

    Per the framework: a wick through that closes back inside is a rejection,
    not a break. Only a close beyond the level counts.
    """
    df = load_bars(db)
    if df.empty:
        return {"error": "No bars in database."}

    day = df[df["bar_date"] == trade_date].reset_index(drop=True)
    if day.empty:
        return {"error": f"No bars for {trade_date}."}

    hi = max(level_00, level_1)
    lo = min(level_00, level_1)

    for idx, bar in day.iterrows():
        if bar["close"] > hi:
            return {
                "break_bar": str(bar["bar_time"]),
                "bar_number": int(idx) + 1,
                "close": round(float(bar["close"]), 2),
                "direction": "buy",
                "range": {"high": hi, "low": lo},
            }
        if bar["close"] < lo:
            return {
                "break_bar": str(bar["bar_time"]),
                "bar_number": int(idx) + 1,
                "close": round(float(bar["close"]), 2),
                "direction": "sell",
                "range": {"high": hi, "low": lo},
            }

    return {
        "break_bar": None,
        "message": "No bar closed outside the open range on this day.",
        "range": {"high": hi, "low": lo},
    }
