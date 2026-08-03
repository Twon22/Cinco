"""
Today's setup.

Answers the question the framework actually cares about: which established
levels are in play right now, above and below current price?

Not today's own range boundaries — those are where a break happens. These are
the known SR levels from prior days that price could travel to and react at.
That reaction is the entry.
"""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import ComputedLevel, Alignment
from app.services.pipeline import load_bars


LEVEL_NAMES = {
    "level_00": "0.0",
    "level_1": "1",
    "level_x_hi": "x$",
    "level_x_lo": "x",
    "level_5_hi": "5$",
    "level_5_lo": "5",
}


def _collect_levels(db: Session, lookback_days: int, include_5: bool) -> list:
    """Every level from recent days, as a flat list."""
    cutoff = date.today() - timedelta(days=lookback_days)
    rows = (
        db.query(ComputedLevel)
        .filter(ComputedLevel.trade_date >= cutoff)
        .filter(ComputedLevel.is_tie.is_(False))
        .order_by(ComputedLevel.trade_date)
        .all()
    )

    fields = ["level_00", "level_1", "level_x_hi", "level_x_lo"]
    if include_5:
        fields += ["level_5_hi", "level_5_lo"]

    out = []
    for r in rows:
        for f in fields:
            v = getattr(r, f)
            if v is None:
                continue
            out.append({
                "date": r.trade_date,
                "label": LEVEL_NAMES[f],
                "price": float(v),
            })
    return out


def _aligned_prices(db: Session, lookback_days: int) -> dict:
    """
    Prices that appear in the alignments table are 'known SR' in the strongest
    sense — two independent days agree on them.
    """
    cutoff = date.today() - timedelta(days=lookback_days)
    rows = (
        db.query(Alignment)
        .filter(Alignment.today_date >= cutoff)
        .all()
    )
    out = {}
    for a in rows:
        for p in (float(a.today_price), float(a.prior_price)):
            key = round(p, 1)
            out.setdefault(key, []).append({
                "today_date": str(a.today_date),
                "prior_date": str(a.prior_date),
                "match_type": a.match_type,
                "diff": float(a.diff),
            })
    return out


def levels_in_play(
    db: Session,
    lookback_days: int = 60,
    max_distance_pips: float = 4000.0,
    include_5: bool = False,
    reference_price: Optional[float] = None,
) -> dict:
    """
    List established levels above and below current price, nearest first.

    reference_price: defaults to the most recent close in the database.
    """
    df = load_bars(db)
    if df.empty:
        return {"error": "No bars in database."}

    last_bar = df.iloc[-1]
    current = reference_price if reference_price is not None else float(last_bar["close"])

    levels = _collect_levels(db, lookback_days, include_5)
    if not levels:
        return {"error": "No computed levels in the lookback window."}

    aligned = _aligned_prices(db, lookback_days)

    above, below = [], []
    for lv in levels:
        dist_pips = abs(lv["price"] - current) * 10
        if dist_pips > max_distance_pips:
            continue

        key = round(lv["price"], 1)
        entry = {
            "price": round(lv["price"], 2),
            "from_date": str(lv["date"]),
            "label": lv["label"],
            "distance_pips": round(dist_pips),
            "aligned": key in aligned,
            "alignment_detail": aligned.get(key, [])[:2],
        }
        (above if lv["price"] > current else below).append(entry)

    above.sort(key=lambda x: x["distance_pips"])
    below.sort(key=lambda x: x["distance_pips"])

    # Group levels sitting within 3 points of each other — a cluster is
    # stronger than a single level
    def cluster(items):
        clusters = []
        for it in sorted(items, key=lambda x: x["price"]):
            if clusters and abs(clusters[-1]["prices"][-1] - it["price"]) <= 3.0:
                clusters[-1]["prices"].append(it["price"])
                clusters[-1]["members"].append(f"{it['from_date']} {it['label']}")
            else:
                clusters.append({
                    "prices": [it["price"]],
                    "members": [f"{it['from_date']} {it['label']}"],
                    "distance_pips": it["distance_pips"],
                    "aligned": it["aligned"],
                })
        return [
            {
                "centre": round(sum(c["prices"]) / len(c["prices"]), 2),
                "count": len(c["prices"]),
                "members": c["members"],
                "distance_pips": c["distance_pips"],
                "aligned": c["aligned"],
            }
            for c in clusters if len(c["prices"]) > 1
        ]

    return {
        "reference_price": round(current, 2),
        "as_of": f"{last_bar['bar_date']} {last_bar['bar_time']}",
        "lookback_days": lookback_days,
        "above": above[:15],
        "below": below[:15],
        "clusters_above": sorted(cluster(above), key=lambda c: c["distance_pips"])[:5],
        "clusters_below": sorted(cluster(below), key=lambda c: c["distance_pips"])[:5],
        "note": (
            "These are established levels from prior days, not today's own range "
            "boundaries. The framework's entry is where price reaches one of "
            "these and rejects — confirmed by the close, not the touch."
        ),
    }
