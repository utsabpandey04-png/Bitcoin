"""
schemas/models.py — Pydantic response models for all API endpoints.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Shared ─────────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total number of matching records")
    limit: int = Field(..., description="Page size used")
    offset: int = Field(..., description="Offset used")
    returned: int = Field(..., description="Number of records in this response")


# ── Transactions ───────────────────────────────────────────────────────────────

class TransactionSummary(BaseModel):
    tx_id: int
    timestep: int
    label: str = Field(..., description="illicit | licit | unknown")
    label_raw: str = Field(..., description="Raw class value: 1, 2, or unknown")

class TransactionDetail(TransactionSummary):
    features: Dict[str, float] = Field(..., description="166 anonymised features")
    out_edges: List[int] = Field(default_factory=list, description="Outgoing neighbour tx IDs")
    in_edges:  List[int] = Field(default_factory=list, description="Incoming neighbour tx IDs")

class TransactionListResponse(BaseModel):
    meta: PaginationMeta
    data: List[TransactionSummary]


# ── Edges ──────────────────────────────────────────────────────────────────────

class Edge(BaseModel):
    source: int = Field(..., description="Source transaction ID (txId1)")
    target: int = Field(..., description="Target transaction ID (txId2)")

class EdgeListResponse(BaseModel):
    meta: PaginationMeta
    data: List[Edge]

class NeighborResponse(BaseModel):
    tx_id: int
    out_neighbors: List[int] = Field(default_factory=list)
    in_neighbors:  List[int] = Field(default_factory=list)
    out_count: int
    in_count: int


# ── Statistics ─────────────────────────────────────────────────────────────────

class ClassCount(BaseModel):
    label: str
    label_raw: str
    count: int
    percentage: float

class OverviewStats(BaseModel):
    total_transactions: int
    total_edges: int
    total_timesteps: int
    class_distribution: List[ClassCount]

class TimestepStats(BaseModel):
    timestep: int
    total: int
    illicit: int
    licit: int
    unknown: int
    illicit_pct: float
    licit_pct: float
    unknown_pct: float

class TimestepStatsResponse(BaseModel):
    data: List[TimestepStats]

class FeatureStat(BaseModel):
    feature: str
    mean: float
    std: float
    min: float
    max: float
    p25: float
    p50: float
    p75: float

class FeatureStatsResponse(BaseModel):
    features: List[FeatureStat]


# ── Graph ──────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    tx_id: int
    timestep: int
    label: str

class GraphEdge(BaseModel):
    source: int
    target: int

class SubgraphResponse(BaseModel):
    root_tx_id: int
    depth: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int

class TimestepGraphResponse(BaseModel):
    timestep: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int
