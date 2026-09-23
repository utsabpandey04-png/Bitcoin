"""
main.py — FastAPI application entry point.

Start the server:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import API_DESCRIPTION, API_TITLE, API_VERSION
from backend.data.loader import load_dataset
from backend.routers import edges, graph, stats, transactions

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up — loading dataset…")
    load_dataset()
    logger.info("✅ Dataset ready. API is live.")
    yield
    logger.info("👋 Shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0       = time.perf_counter()
    response = await call_next(request)
    elapsed  = time.perf_counter() - t0
    response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.2f}"
    return response


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(transactions.router)
app.include_router(edges.router)
app.include_router(stats.router)
app.include_router(graph.router)


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], summary="Health check / API info")
def root():
    return JSONResponse(
        {
            "status": "ok",
            "title": API_TITLE,
            "version": API_VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "transactions": "/api/transactions",
                "edges":        "/api/edges",
                "stats":        "/api/stats",
                "graph":        "/api/graph",
            },
        }
    )
