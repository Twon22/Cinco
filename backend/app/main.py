from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import upload, levels, alignments, trades, pipeline, calibration, outcomes, journey, setup

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cinco API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router,     prefix="/api/upload",     tags=["upload"])
app.include_router(pipeline.router,   prefix="/api/pipeline",   tags=["pipeline"])
app.include_router(levels.router,     prefix="/api/levels",     tags=["levels"])
app.include_router(alignments.router, prefix="/api/alignments", tags=["alignments"])
app.include_router(trades.router,     prefix="/api/trades",     tags=["trades"])
app.include_router(calibration.router, prefix="/api/calibration", tags=["calibration"])
app.include_router(outcomes.router, prefix="/api/outcomes", tags=["outcomes"])
app.include_router(journey.router, prefix="/api/journey", tags=["journey"])
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
@app.get("/")
def health():
    return {"status": "ok", "app": "Cinco"}
