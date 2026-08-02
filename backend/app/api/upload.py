from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ingest import parse_mt4_csv, upsert_bars
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.post("/")
async def upload_csv(
    file: UploadFile = File(...),
    process: bool = Query(True, description="Run the pipeline after uploading"),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    raw = await file.read()
    try:
        df = parse_mt4_csv(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    count = upsert_bars(df, db)

    response = {
        "message": f"Uploaded {count} bars.",
        "rows": count,
        "date_range": {
            "from": str(df["bar_date"].min()),
            "to": str(df["bar_date"].max()),
        },
    }

    if process:
        try:
            response["pipeline"] = run_pipeline(db)
        except Exception as e:
            response["pipeline_error"] = str(e)

    return response
