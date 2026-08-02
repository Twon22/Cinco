# Cinco — Forex Alignment Framework

A daily trading tool built around Fibonacci open-range alignment detection for Gold (XAUUSD).

## What It Does

- Ingests daily H1 OHLC price data exported from MT4
- Computes each day's open range, Fibonacci extension levels (x / x$), and flags tie/gap days
- Scans for x-type alignments across a 5-day window + 3-month boundary-origin lookback
- Presents flagged days for manual chart review and real-entry logging
- Tracks verified trades and running stats

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11 + FastAPI |
| Database | MySQL 8 |
| ORM | SQLAlchemy 2 |
| Frontend | React 18 + Vite |
| Dev environment | VS Code + Docker Compose |

## Project Structure

```
cinco/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Config, DB connection, engine logic
│   │   ├── models/       # SQLAlchemy table models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   └── services/     # Business logic (scanner, computation)
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/   # Reusable UI pieces
│       ├── pages/        # Dashboard, Alignments, Trade Log
│       ├── hooks/        # Data fetching
│       └── utils/        # Formatting helpers
├── docs/                 # Framework notes and pitch doc
└── docker-compose.yml    # MySQL + backend + frontend
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node 18+
- MySQL 8 (or use Docker Compose)
- VS Code with Python and ESLint extensions recommended

### Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in your MySQL credentials
uvicorn app.main:app --reload
```

### Frontend setup
```bash
cd frontend
npm install
npm run dev
```

### With Docker Compose (easiest)
```bash
docker-compose up
```
This starts MySQL, the FastAPI backend, and the React frontend together.

## Daily Workflow

1. After the first 3 H1 bars close, export H1 data from MT4 (Tools → History Center → H1 → Export)
2. Upload the CSV via the dashboard
3. Review any flagged alignment days on your chart
4. Log the real entry (direction, time, price, SR reference) if a setup confirms
5. Outcome is auto-tracked at the 3-day and 4-day mark

## Contributors

- Sean — framework design, pattern discovery, chart validation
- Twon — web application development
