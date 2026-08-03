"""
Cinco computation engine.

Implements the validated rules from the alignment framework:
- Open range detection (3-bar or 4-bar gap rule)
- 0.0 / 1 assignment by chronological order
- Fibonacci extension levels: 5x, x (ratios -4, -5 and 5, 6)
- Tie-day detection
- Alignment scanner: short window + boundary-origin lookback

Scan parameters are configurable so different calibrations can be
compared against each other rather than assumed.
"""

import pandas as pd
from dataclasses import dataclass
from datetime import date
from typing import Optional


GAP_FILL_TOLERANCE = 1.0    # points — misses under this are noise, not real gaps

# Defaults, matching the calibration agreed in the original framework.
ALIGNMENT_TOLERANCE = 3.0   # points — max diff to count as an alignment
BOUNDARY_LOOKBACK_DAYS = 65 # ~3 calendar months of trading days
INTRADAY_WINDOW = 5         # trading days for the short-window scan
BOUNDARY_DAY_START = 5      # day-of-month <= this is "start of month"
BOUNDARY_DAY_END = 26       # day-of-month >= this is "end of month"


@dataclass
class ScanConfig:
    """
    Tunable parameters for one scan run.

    Kept explicit so several calibrations can be run over the same data
    and compared, rather than one setting being hardcoded and trusted.
    """
    tolerance: float = ALIGNMENT_TOLERANCE
    intraday_window: int = INTRADAY_WINDOW
    boundary_lookback: int = BOUNDARY_LOOKBACK_DAYS
    boundary_day_start: int = BOUNDARY_DAY_START
    boundary_day_end: int = BOUNDARY_DAY_END
    include_boundary_matches: bool = True   # allow x vs prior 0.0/1

    def is_boundary_day(self, d: date) -> bool:
        return d.day <= self.boundary_day_start or d.day >= self.boundary_day_end


DEFAULT_CONFIG = ScanConfig()


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
    trading_days_back: int = 0


def _is_boundary_day(d: date) -> bool:
    """Module-level helper retained for backwards compatibility."""
    return DEFAULT_CONFIG.is_boundary_day(d)


def compute_levels(
    bars: pd.DataFrame,
    prior_close: Optional[float] = None,
    prior_bar: Optional[dict] = None,
) -> DayLevels:
    """
    bars:        DataFrame of THIS trading day's H1 bars only, sorted ascending.
                 Columns: [bar_date, bar_time, open, high, low, close]
    prior_close: closing price of the prior trading day's final bar.
    prior_bar:   the prior trading day's final bar as a dict with
                 'high' and 'low' keys. Required to build a 4-bar range
                 when an unfilled gap is detected.
    """
    trade_date = bars["bar_date"].iloc[0]
    result = DayLevels(trade_date=trade_date)

    first3 = bars.iloc[:3]
    is_gap = False

    if prior_close is not None:
        gap = abs(first3.iloc[0]["open"] - prior_close)
        if gap > GAP_FILL_TOLERANCE:
            fills = (first3["low"].min() <= prior_close <= first3["high"].max())
            is_gap = not fills

    result.is_gap = is_gap

    highs = list(first3["high"])
    lows = list(first3["low"])

    if is_gap:
        if prior_bar is None:
            raise ValueError(
                f"{trade_date}: unfilled gap detected but prior_bar was not "
                "supplied — cannot build the 4-bar open range."
            )
        highs.insert(0, prior_bar["high"])
        lows.insert(0, prior_bar["low"])

    high_idx = highs.index(max(highs))
    low_idx = lows.index(min(lows))

    if high_idx == low_idx:
        result.is_tie = True
        return result

    range_high = max(highs)
    range_low = min(lows)

    if high_idx < low_idx:
        point1, point2 = range_high, range_low   # high first → 1 = high
    else:
        point1, point2 = range_low, range_high   # low first  → 1 = low

    span = point2 - point1

    result.level_1  = round(float(point1), 2)
    result.level_00 = round(float(point2), 2)

    result.level_5_hi = round(float(point1 + 5 * span), 2)   # $5x
    result.level_x_hi = round(float(point1 + 6 * span), 2)   # $x
    result.level_5_lo = round(float(point1 - 4 * span), 2)   # 5x
    result.level_x_lo = round(float(point1 - 5 * span), 2)   # x

    return result


def _x_levels(dl: DayLevels) -> dict:
    """Only the x-type levels. 5 / 5$ are never matched on either side."""
    return {
        "x_hi": dl.level_x_hi,
        "x_lo": dl.level_x_lo,
    }


def _target_levels(dl: DayLevels, include_boundary: bool) -> dict:
    targets = {
        "x_hi": dl.level_x_hi,
        "x_lo": dl.level_x_lo,
    }
    if include_boundary:
        targets["level_00"] = dl.level_00
        targets["level_1"] = dl.level_1
    return targets


def scan_alignments(
    today: DayLevels,
    history: list[DayLevels],
    config: ScanConfig = DEFAULT_CONFIG,
) -> list[AlignmentMatch]:
    """
    history: list of DayLevels, most-recent first.

    Rules:
    - Short window: today's x vs prior levels within config.intraday_window
      trading days.
    - Boundary-origin: if a prior day falls at a month boundary, its levels
      stay checkable for config.boundary_lookback trading days.
    - 5 / 5$ levels are never matched on either side.
    - Tie days are skipped as both today and prior.
    """
    if today.is_tie or today.level_x_hi is None:
        return []

    today_x = _x_levels(today)
    matches: list[AlignmentMatch] = []
    today_is_boundary = config.is_boundary_day(today.trade_date)

    for i, prior in enumerate(history):
        if prior.is_tie or prior.level_x_hi is None:
            continue

        trading_days_back = i + 1
        prior_is_boundary = config.is_boundary_day(prior.trade_date)

        in_short_window = trading_days_back <= config.intraday_window
        in_boundary_window = (
            prior_is_boundary and trading_days_back <= config.boundary_lookback
        )

        if not (in_short_window or in_boundary_window):
            continue

        prior_targets = _target_levels(prior, config.include_boundary_matches)

        for t_label, t_price in today_x.items():
            if t_price is None:
                continue
            for p_label, p_price in prior_targets.items():
                if p_price is None:
                    continue
                diff = abs(t_price - p_price)
                if diff <= config.tolerance:
                    p_is_x = p_label.startswith("x")
                    matches.append(AlignmentMatch(
                        today_date=today.trade_date,
                        prior_date=prior.trade_date,
                        today_level=t_label,
                        prior_level=p_label,
                        today_price=t_price,
                        prior_price=p_price,
                        diff=round(diff, 2),
                        match_type="x==x" if p_is_x else "x==boundary",
                        is_boundary_day=today_is_boundary or prior_is_boundary,
                        trading_days_back=trading_days_back,
                    ))

    return matches
