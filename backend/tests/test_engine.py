"""
Unit tests for the Cinco computation engine.

These verify the RULES work correctly using hand-constructed bar data.
They do not require the real MT4 export.

Run with:  pytest backend/tests/test_engine.py -v
"""

import pandas as pd
import pytest
from datetime import date

from app.services.engine import (
    compute_levels,
    scan_alignments,
    DayLevels,
    GAP_FILL_TOLERANCE,
    ALIGNMENT_TOLERANCE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bars(rows, trade_date=date(2026, 3, 18)):
    """
    rows: list of (time_str, open, high, low, close)
    Returns a DataFrame shaped the way compute_levels expects.
    """
    return pd.DataFrame([
        {
            "bar_date": trade_date,
            "bar_time": t,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
        }
        for (t, o, h, l, c) in rows
    ])


# ---------------------------------------------------------------------------
# 0.0 / 1 assignment rule
# ---------------------------------------------------------------------------

def test_low_first_assigns_1_to_low():
    """
    Rule: if the low is reached first chronologically,
    then 1 = the low and 0.0 = the high.
    """
    bars = make_bars([
        ("01:00", 100.0, 105.0, 95.0, 102.0),   # low of the window: 95
        ("02:00", 102.0, 108.0, 101.0, 107.0),
        ("03:00", 107.0, 110.0, 106.0, 109.0),  # high of the window: 110
    ])
    result = compute_levels(bars)

    assert result.is_tie is False
    assert result.level_1 == 95.0
    assert result.level_00 == 110.0


def test_high_first_assigns_1_to_high():
    """
    Rule: if the high is reached first chronologically,
    then 1 = the high and 0.0 = the low.
    """
    bars = make_bars([
        ("01:00", 100.0, 110.0, 99.0, 105.0),   # high of the window: 110
        ("02:00", 105.0, 106.0, 98.0, 100.0),
        ("03:00", 100.0, 101.0, 95.0, 96.0),    # low of the window: 95
    ])
    result = compute_levels(bars)

    assert result.is_tie is False
    assert result.level_1 == 110.0
    assert result.level_00 == 95.0


# ---------------------------------------------------------------------------
# Extension level formulas
# ---------------------------------------------------------------------------

def test_extension_levels_low_first():
    """
    With 1 = 95 and 0.0 = 110, span = 0.0 - 1 = +15.
    Extensions from point1 (=1):
      $5x (ratio 5) = 95 + 5*15  = 170
      $x  (ratio 6) = 95 + 6*15  = 185
      5x  (ratio -4)= 95 - 4*15  = 35
      x   (ratio -5)= 95 - 5*15  = 20
    """
    bars = make_bars([
        ("01:00", 100.0, 105.0, 95.0, 102.0),
        ("02:00", 102.0, 108.0, 101.0, 107.0),
        ("03:00", 107.0, 110.0, 106.0, 109.0),
    ])
    result = compute_levels(bars)

    assert result.level_5_hi == 170.0
    assert result.level_x_hi == 185.0
    assert result.level_5_lo == 35.0
    assert result.level_x_lo == 20.0


def test_extension_levels_high_first_invert():
    """
    With 1 = 110 and 0.0 = 95, span = 95 - 110 = -15.
    Extensions flip direction:
      $5x = 110 + 5*(-15) = 35
      $x  = 110 + 6*(-15) = 20
      5x  = 110 - 4*(-15) = 170
      x   = 110 - 5*(-15) = 185
    """
    bars = make_bars([
        ("01:00", 100.0, 110.0, 99.0, 105.0),
        ("02:00", 105.0, 106.0, 98.0, 100.0),
        ("03:00", 100.0, 101.0, 95.0, 96.0),
    ])
    result = compute_levels(bars)

    assert result.level_5_hi == 35.0
    assert result.level_x_hi == 20.0
    assert result.level_5_lo == 170.0
    assert result.level_x_lo == 185.0


# ---------------------------------------------------------------------------
# Tie days
# ---------------------------------------------------------------------------

def test_tie_day_is_flagged_and_levels_left_blank():
    """
    When the same bar contains both the window's high and low,
    chronological order is unknowable from H1 data alone.
    The day must be flagged and no levels assigned.
    """
    bars = make_bars([
        ("01:00", 100.0, 120.0, 80.0, 90.0),   # this bar holds BOTH extremes
        ("02:00", 90.0, 95.0, 88.0, 92.0),
        ("03:00", 92.0, 99.0, 91.0, 98.0),
    ])
    result = compute_levels(bars)

    assert result.is_tie is True
    assert result.level_00 is None
    assert result.level_1 is None
    assert result.level_x_hi is None


# ---------------------------------------------------------------------------
# Gap rule
# ---------------------------------------------------------------------------

def test_small_gap_is_treated_as_noise():
    """
    A gap smaller than GAP_FILL_TOLERANCE (1.0) is noise, not a real gap.
    The 3-bar window should be used.
    """
    bars = make_bars([
        ("01:00", 100.5, 105.0, 95.0, 102.0),
        ("02:00", 102.0, 108.0, 101.0, 107.0),
        ("03:00", 107.0, 110.0, 106.0, 109.0),
        ("04:00", 109.0, 200.0, 50.0, 150.0),   # would distort if included
    ])
    result = compute_levels(bars, prior_close=100.0)   # 0.5 point gap

    assert result.is_gap is False
    assert result.level_1 == 95.0
    assert result.level_00 == 110.0


def test_unfilled_gap_uses_four_bars():
    """
    A gap larger than tolerance that does NOT fill within the first 3 bars
    is a real gap, so the prior bar is prepended (4-bar window).
    """
    bars = make_bars([
        ("01:00", 100.0, 105.0, 95.0, 102.0),
        ("02:00", 102.0, 108.0, 101.0, 107.0),
        ("03:00", 107.0, 110.0, 106.0, 109.0),
    ])
    prior = {"high": 52.0, "low": 48.0, "close": 51.0}
    # prior_close of 51 is far below the 95-110 range → never fills
    result = compute_levels(bars, prior_close=51.0, prior_bar=prior)

    assert result.is_gap is True
    # The prior bar came FIRST chronologically and holds the low (48),
    # so 1 = 48 and 0.0 = 110.
    assert result.level_1 == 48.0
    assert result.level_00 == 110.0


def test_gap_that_fills_within_three_bars_is_not_a_gap():
    """
    If price trades back through the prior close within the first 3 bars,
    the gap effectively closed — use 3 bars, not 4.
    """
    bars = make_bars([
        ("01:00", 100.0, 105.0, 95.0, 102.0),   # range 95-105 contains 98
        ("02:00", 102.0, 108.0, 101.0, 107.0),
        ("03:00", 107.0, 110.0, 106.0, 109.0),
    ])
    result = compute_levels(bars, prior_close=98.0)   # 2-point gap, but fills

    assert result.is_gap is False


# ---------------------------------------------------------------------------
# Alignment scanner
# ---------------------------------------------------------------------------

def make_day(d, x_hi=None, x_lo=None, level_00=None, level_1=None, is_tie=False):
    return DayLevels(
        trade_date=d,
        level_00=level_00,
        level_1=level_1,
        level_x_hi=x_hi,
        level_x_lo=x_lo,
        is_tie=is_tie,
    )


def test_x_to_x_match_within_tolerance():
    """Two x-levels within 3 points should match, classified as x==x."""
    today = make_day(date(2026, 3, 18), x_hi=5107.75, x_lo=4900.0)
    prior = make_day(date(2026, 3, 17), x_hi=6000.0, x_lo=5105.58)

    matches = scan_alignments(today, [prior])

    assert len(matches) == 1
    assert matches[0].match_type == "x==x"
    assert matches[0].diff == 2.17


def test_x_to_boundary_match_is_classified_separately():
    """An x matching a prior 0.0 or 1 is the weaker 'x==boundary' type."""
    today = make_day(date(2026, 1, 21), x_hi=4755.68, x_lo=1000.0)
    prior = make_day(date(2026, 1, 16), x_hi=9000.0, x_lo=8000.0,
                     level_1=4757.63, level_00=3000.0)

    matches = scan_alignments(today, [prior])

    assert len(matches) == 1
    assert matches[0].match_type == "x==boundary"


def test_no_match_outside_tolerance():
    """A 50-point difference is far outside the 3-point tolerance."""
    today = make_day(date(2026, 3, 18), x_hi=5100.0, x_lo=4900.0)
    prior = make_day(date(2026, 3, 17), x_hi=5150.0, x_lo=4850.0)

    assert scan_alignments(today, [prior]) == []


def test_tie_day_is_skipped_as_today():
    """A tie day can't be scanned — no levels exist to compare."""
    today = make_day(date(2026, 6, 17), is_tie=True)
    prior = make_day(date(2026, 6, 16), x_hi=5100.0, x_lo=4900.0)

    assert scan_alignments(today, [prior]) == []


def test_tie_day_is_skipped_as_prior():
    """A tie day also can't serve as a comparison target."""
    today = make_day(date(2026, 6, 18), x_hi=5100.0, x_lo=4900.0)
    prior = make_day(date(2026, 6, 17), x_hi=5100.5, x_lo=4899.5, is_tie=True)

    assert scan_alignments(today, [prior]) == []


def test_five_levels_are_never_matched():
    """
    5 and 5$ are excluded from matching on both sides.
    A prior day whose ONLY near level is a 5-type should produce no match.
    """
    today = make_day(date(2026, 3, 18), x_hi=5100.0, x_lo=4900.0)
    prior = DayLevels(
        trade_date=date(2026, 3, 17),
        level_5_hi=5100.5,   # extremely close, but a 5-type
        level_5_lo=4899.5,
        level_x_hi=9999.0,   # x-levels far away
        level_x_lo=1.0,
    )

    assert scan_alignments(today, [prior]) == []


def test_short_window_excludes_distant_non_boundary_days():
    """
    A non-boundary prior day more than 5 trading days back
    should not be checked.
    """
    today = make_day(date(2026, 3, 18), x_hi=5100.0, x_lo=4900.0)
    # 7 filler days, then the matching day at position 8
    history = [make_day(date(2026, 3, 17 - i), x_hi=9000.0, x_lo=1000.0)
               for i in range(7)]
    history.append(make_day(date(2026, 3, 10), x_hi=5100.5, x_lo=1.0))

    assert scan_alignments(today, history) == []


def test_boundary_origin_day_stays_checkable_beyond_short_window():
    """
    A prior day at a month boundary (day <= 5 or >= 26) remains checkable
    for up to ~3 months, even though it's outside the 5-day window.
    """
    today = make_day(date(2026, 3, 18), x_hi=5100.0, x_lo=4900.0)
    history = [make_day(date(2026, 3, 17), x_hi=9000.0, x_lo=1000.0)
               for _ in range(10)]
    # A boundary day (the 2nd) sitting well outside the 5-day window
    history.append(make_day(date(2026, 3, 2), x_hi=5100.5, x_lo=1.0))

    matches = scan_alignments(today, history)

    assert len(matches) == 1
    assert matches[0].prior_date == date(2026, 3, 2)
    assert matches[0].is_boundary_day is True
