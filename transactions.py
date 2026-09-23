"""
routers/transactions.py — Endpoints for querying transaction nodes.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import DEFAULT_LIMIT, MAX_LIMIT, FEATURE_NAMES
from backend.data.loader import (
    DataStore,
    get_store,
    get_node_row,
    get_feature_row,
    get_out_neighbors,
    get_in_neighbors,
    node_exists,
)
from backend.schemas.models import (
    PaginationMeta,
    TransactionDetail,
    TransactionListResponse,
    TransactionSummary,
)

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _row_to_summary(tx_id: int, row) -> TransactionSummary:
    return TransactionSummary(
        tx_id=int(tx_id),
        timestep=int(row["timestep"]),
        label=str(row["label"]),
        label_raw=str(row["label_raw"]),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=TransactionListResponse,
    summary="List transactions",
    description=(
        "Paginated list of transactions. Optionally filter by class label "
        "(`illicit`, `licit`, `unknown`) and/or timestep."
    ),
)
def list_transactions(
    store: Annotated[DataStore, Depends(get_store)],
    label: Optional[str] = Query(
        None,
        description="Filter by label: illicit | licit | unknown",
        pattern="^(illicit|licit|unknown)$",
    ),
    timestep: Optional[int] = Query(
        None, ge=1, le=49, description="Filter by timestep (1-49)"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
):
    df = store.nodes_df

    if label is not None:
        df = df[df["label"] == label]
    if timestep is not None:
        df = df[df["timestep"] == timestep]

    total = len(df)
    page  = df.iloc[offset : offset + limit]

    data = [_row_to_summary(tx_id, row) for tx_id, row in page.iterrows()]

    return TransactionListResponse(
        meta=PaginationMeta(
            total=total, limit=limit, offset=offset, returned=len(data)
        ),
        data=data,
    )


@router.get(
    "/search",
    response_model=TransactionListResponse,
    summary="Search / filter transactions",
    description="Filter transactions by multiple criteria simultaneously.",
)
def search_transactions(
    store: Annotated[DataStore, Depends(get_store)],
    label: Optional[str] = Query(None, pattern="^(illicit|licit|unknown)$"),
    timestep_min: Optional[int] = Query(None, ge=1, le=49),
    timestep_max: Optional[int] = Query(None, ge=1, le=49),
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    df = store.nodes_df

    if label is not None:
        df = df[df["label"] == label]
    if timestep_min is not None:
        df = df[df["timestep"] >= timestep_min]
    if timestep_max is not None:
        df = df[df["timestep"] <= timestep_max]

    total = len(df)
    page  = df.iloc[offset : offset + limit]
    data  = [_row_to_summary(tx_id, row) for tx_id, row in page.iterrows()]

    return TransactionListResponse(
        meta=PaginationMeta(total=total, limit=limit, offset=offset, returned=len(data)),
        data=data,
    )


@router.get(
    "/{tx_id}",
    response_model=TransactionDetail,
    summary="Get transaction by ID",
    description="Returns full details for a single transaction: label, timestep, all 166 features, and its neighbours.",
)
def get_transaction(
    tx_id: int,
    store: Annotated[DataStore, Depends(get_store)],
):
    if not node_exists(tx_id):
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found.")

    node = get_node_row(tx_id)
    feat = get_feature_row(tx_id)

    features = {name: float(feat[name]) for name in FEATURE_NAMES}

    return TransactionDetail(
        tx_id=int(tx_id),
        timestep=int(node["timestep"]),
        label=str(node["label"]),
        label_raw=str(node["label_raw"]),
        features=features,
        out_edges=get_out_neighbors(tx_id),
        in_edges=get_in_neighbors(tx_id),
    )
