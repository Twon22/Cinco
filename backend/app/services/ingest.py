"""
Parses MT4 H1 CSV exports and upserts into daily_bars.

MT4 export format (no header):
  YYYY.MM.DD,HH:MM,Open,High,Low,Close,Volume
"""

import pandas as pd
import io
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from app.models.models import DailyBar


def parse_mt4_csv(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(
        io.BytesIO(raw),
        header=None,
        names=["date_str", "time_str", "open", "high", "low", "close", "volume"],
    )
    df["bar_date"] = pd.to_datetime(df["date_str"], format="%Y.%m.%d").dt.date
    df["bar_time"] = pd.to_datetime(df["time_str"], format="%H:%M").dt.time
    df = df.drop(columns=["date_str", "time_str"])
    df = df.sort_values(["bar_date", "bar_time"]).reset_index(drop=True)
    return df


def upsert_bars(df: pd.DataFrame, db: Session) -> int:
    """Upsert rows into daily_bars. Returns number of rows processed."""
    rows = df.to_dict(orient="records")
    stmt = insert(DailyBar).values(rows)
    stmt = stmt.on_duplicate_key_update(
        open=stmt.inserted.open,
        high=stmt.inserted.high,
        low=stmt.inserted.low,
        close=stmt.inserted.close,
        volume=stmt.inserted.volume,
    )
    db.execute(stmt)
    db.commit()
    return len(rows)
