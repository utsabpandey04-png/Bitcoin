"""
config.py — Centralised application configuration.
All dataset paths and tuneable settings live here.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # Bitcoin/
DATASET_DIR = BASE_DIR / "archive" / "elliptic_bitcoin_dataset"

FEATURES_CSV  = DATASET_DIR / "elliptic_txs_features.csv"
CLASSES_CSV   = DATASET_DIR / "elliptic_txs_classes.csv"
EDGELIST_CSV  = DATASET_DIR / "elliptic_txs_edgelist.csv"

# ── Server ─────────────────────────────────────────────────────────────────────
API_TITLE       = "Bitcoin Elliptic Analytics API"
API_VERSION     = "1.0.0"
API_DESCRIPTION = (
    "REST API for exploring and analysing the Elliptic Bitcoin transaction dataset. "
    "Query transactions, edges, graph neighbourhoods, and summary statistics."
)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# ── Pagination defaults ────────────────────────────────────────────────────────
DEFAULT_LIMIT = 50
MAX_LIMIT     = 1000

# ── Feature column names ───────────────────────────────────────────────────────
# features CSV has no header: col0=txId, col1=timestep, col2..167 = 166 features
N_FEATURES      = 166
FEATURE_NAMES   = [f"feature_{i}" for i in range(1, N_FEATURES + 1)]

# Human-readable class map
CLASS_MAP = {"1": "illicit", "2": "licit", "unknown": "unknown"}
