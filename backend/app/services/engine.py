"""
Cinco computation engine.

Implements the validated rules from the alignment framework:
- Open range detection (3-bar or 4-bar gap rule)
- 0.0 / 1 assignment by chronological order
- Fibonacci extension levels: 5x, x (ratios -4, -5 and 5, 6)
- Tie-day detection
- Alignment scanner: 5-day window + 3-month boundary-origin lookback
"""

import pandas as pd
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


GAP_FILL_TOLERANCE = 1.0    # points — misses under this are noise, not real gaps
ALIGNMENT_TOLERANCE = 3.0   # points — max diff to count as an alignment
BOUNDARY_LOOKBACK_DAYS = 65 # ~3 calendar months of trading days
INTRADAY_WINDOW = 5         # trading days for the short-window scan
BOUNDARY_DAY_START = 5      # day-of-month <= this is "start of month"
BOUNDARY_DAY_END = 26       # day-of-month >= this is "end of month"


@dataclass
class DayLevels:
    trade_date: date
    level_00: Optional[float] = None
    level_1: Optional[float] = None
    level_5_hi: Optional[float] = None   # $5x  ratio +5
    level_x_hi: Optional[float] = None   # $x   ratio +6
    level_5_lo: Optional[float] = None   # 5x   ratio -4
    level_x_lo: Optional[float] = None   # x    ratio -5
    is_tie: bool = False
    is_gap: bool = False
    is_nested: Optional[bool] = None


@dataclass
class AlignmentMatch:
    today_date: date
    prior_date: date
    today_level: str
    prior_level: str
    today_price: float
    prior_price: float
    diff: float
    match_type: str          # 'x==x' or 'x==boundary'
    is_boundary_day: bool = False


def _is_boundary_day(d: date) -> bool:
    return d.day <= BOUNDARY_DAY_START or d.day >= BOUNDARY_DAY_END


def compute_levels(bars: pd.DataFrame, prior_close: Optional[float] = None) -> DayLevels:
    """
    bars: DataFrame with columns [bar_time, open, high, low, close], sorted ascending.
          Must contain at least the first 3 (or 4) H1 bars of the trading day.
    prior_close: closing price of the last bar of the prior trading day.

    Returns a DayLevels instance.
    """
    trade_date = bars["bar_date"].iloc[0]
    result = DayLevels(trade_date=trade_date)

    first_open = bars.iloc[0]["open"]
    is_gap = False

    if prior_close is not None:
        gap = abs(first_open - prior_close)
        if gap > GAP_FILL_TOLERANCE:
            # Check if the gap fills within the first 3 bars
            first3 = bars.iloc[:3]
            low3 = first3["low"].min()
            high3 = first3["high"].max()
            fills = (low3 <= prior_close <= high3)
            if not fills:
                is_gap = True

    result.is_gap = is_gap
    range_bars = bars.iloc[:4] if is_gap else bars.iloc[:3]

    range_high = range_bars["high"].max()
    range_low = range_bars["low"].min()

    # Tie: same bar holds both the high and the low
    high_bar_idx = range_bars["high"].idxmax()
    low_bar_idx = range_bars["low"].idxmin()
    if high_bar_idx == low_bar_idx:
        result.is_tie = True
        return result  # Cannot assign 0.0/1 without chart confirmation

    # Chronological order determines 0.0 vs 1
    if high_bar_idx < low_bar_idx:
        # High came first → 1 = high, 0.0 = low
        point1 = range_high   # 1
        point2 = range_low    # 0.0
    else:
        # Low came first → 1 = low, 0.0 = high
        point1 = range_low    # 1
        point2 = range_high   # 0.0

    span = point2 - point1   # positive when 0.0 > 1, negative otherwise

    result.level_1  = round(point1, 2)
    result.level_00 = round(point2, 2)

    # Extensions: ratios from point1 in the direction of span
    result.level_5_hi = round(point1 + 5 * span, 2)   # $5x
    result.level_x_hi = round(point1 + 6 * span, 2)   # $x
    result.level_5_lo = round(point1 - 4 * span, 2)   # 5x
    result.level_x_lo = round(point1 - 5 * span, 2)   # x

    return result


def _x_levels(dl: DayLevels) -> dict:
    """Return only the x-type levels (excluding 5 / 5$)."""
    return {
        "x_hi": dl.level_x_hi,
        "x_lo": dl.level_x_lo,
    }


def _all_levels(dl: DayLevels) -> dict:
    """Return all levels including boundary ones (0.0, 1) for SR matching."""
    return {
        "level_00": dl.level_00,
        "level_1": dl.level_1,
        "x_hi": dl.level_x_hi,
        "x_lo": dl.level_x_lo,
    }


def scan_alignments(
    today: DayLevels,
    history: list[DayLevels],
) -> list[AlignmentMatch]:
    """
    history: list of DayLevels, most-recent first, covering at least
             BOUNDARY_LOOKBACK_DAYS worth of trading days.

    Rules:
    - 5-day intraday window: today's x vs ALL prior levels (x and boundary)
    - Boundary-origin levels: if a prior day is a boundary day, its x-levels
      stay checkable for up to BOUNDARY_LOOKBACK_DAYS trading days.
    - 5 / 5$ levels are never matched on either side.
    - Tie days are skipped as both today and prior.
    """
    if today.is_tie or today.level_x_hi is None:
        return []

    today_x = _x_levels(today)
    matches: list[AlignmentMatch] = []
    today_is_boundary = _is_boundary_day(today.trade_date)

    for i, prior in enumerate(history):
        if prior.is_tie or prior.level_x_hi is None:
            continue

        trading_days_back = i + 1
        prior_is_boundary = _is_boundary_day(prior.trade_date)

        in_short_window = trading_days_back <= INTRADAY_WINDOW
        in_boundary_window = prior_is_boundary and trading_days_back <= BOUNDARY_LOOKBACK_DAYS

        if not (in_short_window or in_boundary_window):
            continue

        prior_all = _all_levels(prior)

        for t_label, t_price in today_x.items():
            if t_price is None:
                continue
            for p_label, p_price in prior_all.items():
                if p_price is None:
                    continue
                diff = abs(t_price - p_price)
                if diff <= ALIGNMENT_TOLERANCE:
                    p_is_x = p_label.startswith("x")
                    match_type = "x==x" if p_is_x else "x==boundary"
                    matches.append(AlignmentMatch(
                        today_date=today.trade_date,
                        prior_date=prior.trade_date,
                        today_level=t_label,
                        prior_level=p_label,
                        today_price=t_price,
                        prior_price=p_price,
                        diff=round(diff, 2),
                        match_type=match_type,
                        is_boundary_day=today_is_boundary or prior_is_boundary,
                    ))

    return matches
