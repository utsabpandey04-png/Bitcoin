"""
routers/graph.py — Graph traversal and timestep snapshot endpoints.
"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.data.loader import (
    DataStore,
    bfs_subgraph,
    get_store,
    get_timestep_tx_ids,
    node_exists,
)
from backend.schemas.models import (
    GraphEdge,
    GraphNode,
    SubgraphResponse,
    TimestepGraphResponse,
)

router = APIRouter(prefix="/api/graph", tags=["Graph"])


def _tx_ids_to_nodes(tx_ids: List[int], store: DataStore) -> List[GraphNode]:
    nodes_df = store.nodes_df
    result: List[GraphNode] = []
    for tx_id in tx_ids:
        if tx_id in store.all_tx_ids:
            row = nodes_df.loc[tx_id]
            result.append(
                GraphNode(
                    tx_id=int(tx_id),
                    timestep=int(row["timestep"]),
                    label=str(row["label"]),
                )
            )
    return result


@router.get(
    "/subgraph",
    response_model=SubgraphResponse,
    summary="BFS subgraph around a transaction",
    description=(
        "Performs a bidirectional BFS from `tx_id` up to `depth` hops. "
        "Returns all reachable nodes and edges (capped at `max_nodes` nodes)."
    ),
)
def get_subgraph(
    store: Annotated[DataStore, Depends(get_store)],
    tx_id: int = Query(..., description="Root transaction ID"),
    depth: int = Query(2, ge=1, le=5, description="BFS depth (max 5)"),
    max_nodes: int = Query(300, ge=1, le=500, description="Max nodes to return"),
):
    if not node_exists(tx_id):
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found.")

    node_ids, edge_pairs = bfs_subgraph(tx_id, depth, max_nodes)

    nodes = _tx_ids_to_nodes(node_ids, store)
    edges = [GraphEdge(source=s, target=t) for s, t in edge_pairs]

    return SubgraphResponse(
        root_tx_id=tx_id,
        depth=depth,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


@router.get(
    "/timestep/{timestep}",
    response_model=TimestepGraphResponse,
    summary="Transaction graph for a single timestep",
    description=(
        "Returns all transaction nodes and edges that belong to the given "
        "timestep (1-49). Edges where BOTH endpoints are in this timestep are included."
    ),
)
def timestep_graph(
    timestep: int,
    store: Annotated[DataStore, Depends(get_store)],
):
    if timestep < 1 or timestep > 49:
        raise HTTPException(status_code=422, detail="Timestep must be between 1 and 49.")

    tx_ids = get_timestep_tx_ids(timestep)
    if not tx_ids:
        raise HTTPException(status_code=404, detail=f"No transactions found for timestep {timestep}.")

    tx_set = set(tx_ids)
    nodes  = _tx_ids_to_nodes(tx_ids, store)

    # Only include edges where BOTH endpoints are in this timestep
    edges: List[GraphEdge] = []
    for src in tx_ids:
        for tgt in store.out_adj.get(src, []):
            if tgt in tx_set:
                edges.append(GraphEdge(source=src, target=tgt))

    return TimestepGraphResponse(
        timestep=timestep,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )
