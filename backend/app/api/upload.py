from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ingest import parse_mt4_csv, upsert_bars

router = APIRouter()


@router.post("/")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    raw = await file.read()
    try:
        df = parse_mt4_csv(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")
    count = upsert_bars(df, db)
    return {"message": f"Uploaded {count} bars successfully.", "rows": count}
