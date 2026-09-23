"""
routers/edges.py — Endpoints for querying edges and neighbourhoods.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import DEFAULT_LIMIT, MAX_LIMIT
from backend.data.loader import (
    DataStore,
    get_store,
    get_in_neighbors,
    get_out_neighbors,
    node_exists,
)
from backend.schemas.models import (
    Edge,
    EdgeListResponse,
    NeighborResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/api/edges", tags=["Edges"])


@router.get(
    "",
    response_model=EdgeListResponse,
    summary="List edges",
    description="Paginated list of all directed edges in the transaction graph.",
)
def list_edges(
    store: Annotated[DataStore, Depends(get_store)],
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    df    = store.edges_df
    total = len(df)
    page  = df.iloc[offset : offset + limit]

    data = [
        Edge(source=int(row["source"]), target=int(row["target"]))
        for _, row in page.iterrows()
    ]

    return EdgeListResponse(
        meta=PaginationMeta(total=total, limit=limit, offset=offset, returned=len(data)),
        data=data,
    )


@router.get(
    "/{tx_id}/neighbors",
    response_model=NeighborResponse,
    summary="Get neighbours of a transaction",
    description=(
        "Returns all direct (1-hop) incoming and outgoing neighbours "
        "of the given transaction ID."
    ),
)
def get_neighbors(
    tx_id: int,
    store: Annotated[DataStore, Depends(get_store)],
):
    if not node_exists(tx_id):
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found.")

    out = get_out_neighbors(tx_id)
    inn = get_in_neighbors(tx_id)

    return NeighborResponse(
        tx_id=tx_id,
        out_neighbors=out,
        in_neighbors=inn,
        out_count=len(out),
        in_count=len(inn),
    )
