"""
data/loader.py — Single-responsibility module for loading and caching the
Elliptic Bitcoin dataset into memory at application startup.

Dataset layout
--------------
elliptic_txs_features.csv  (no header)
    col 0  : txId
    col 1  : timestep  (1-49)
    col 2+ : 166 anonymised features

elliptic_txs_classes.csv   (has header: txId, class)
    class  : "1" = illicit | "2" = licit | "unknown"

elliptic_txs_edgelist.csv  (has header: txId1, txId2)
    directed edge from txId1 → txId2
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from backend.config import (
    CLASSES_CSV,
    EDGELIST_CSV,
    FEATURE_NAMES,
    FEATURES_CSV,
    N_FEATURES,
    CLASS_MAP,
)

logger = logging.getLogger(__name__)


# ── Singleton store ────────────────────────────────────────────────────────────

class DataStore:
    """Holds all dataset artefacts after loading."""

    # Core DataFrames
    features_df: pd.DataFrame    # index=txId, cols=[timestep, feature_1..feature_166]
    classes_df:  pd.DataFrame    # index=txId, cols=[class_raw, label]
    edges_df:    pd.DataFrame    # cols=[source, target]

    # Merged node info (no feature cols — lightweight lookup)
    nodes_df: pd.DataFrame       # index=txId, cols=[timestep, label, label_raw]

    # Adjacency maps (txId → sorted list of neighbours)
    out_adj: Dict[int, List[int]]   # txId → list of outgoing neighbours
    in_adj:  Dict[int, List[int]]   # txId → list of incoming neighbours

    # Timestep index: timestep → list of txIds
    timestep_index: Dict[int, List[int]]

    # Sorted unique tx_ids for fast existence checks
    all_tx_ids: Set[int]

    loaded: bool = False


_store = DataStore()


def get_store() -> DataStore:
    """FastAPI dependency — returns the loaded data store."""
    return _store


# ── Loading logic ──────────────────────────────────────────────────────────────

def _load_features() -> pd.DataFrame:
    """Load features CSV (no header). Returns df indexed by txId."""
    logger.info("Loading features CSV (this may take a moment)…")
    t0 = time.perf_counter()

    col_names = ["tx_id", "timestep"] + FEATURE_NAMES
    dtype_map = {"tx_id": np.int64, "timestep": np.int8}
    for f in FEATURE_NAMES:
        dtype_map[f] = np.float32

    df = pd.read_csv(
        FEATURES_CSV,
        header=None,
        names=col_names,
        dtype=dtype_map,
    )
    df.set_index("tx_id", inplace=True)

    elapsed = time.perf_counter() - t0
    logger.info("Features loaded: %d rows in %.1fs", len(df), elapsed)
    return df


def _load_classes() -> pd.DataFrame:
    """Load classes CSV. Returns df indexed by txId with label columns."""
    logger.info("Loading classes CSV…")
    df = pd.read_csv(CLASSES_CSV, dtype={"txId": np.int64, "class": str})
    df.rename(columns={"txId": "tx_id", "class": "label_raw"}, inplace=True)
    df["label"] = df["label_raw"].map(CLASS_MAP).fillna("unknown")
    df.set_index("tx_id", inplace=True)
    logger.info("Classes loaded: %d rows", len(df))
    return df


def _load_edges() -> pd.DataFrame:
    """Load edgelist CSV. Returns df with columns [source, target]."""
    logger.info("Loading edgelist CSV…")
    df = pd.read_csv(EDGELIST_CSV, dtype={"txId1": np.int64, "txId2": np.int64})
    df.rename(columns={"txId1": "source", "txId2": "target"}, inplace=True)
    logger.info("Edges loaded: %d rows", len(df))
    return df


def _build_adjacency(edges_df: pd.DataFrame) -> Tuple[Dict[int, List[int]], Dict[int, List[int]]]:
    """Build outgoing and incoming adjacency dicts."""
    logger.info("Building adjacency maps…")
    out_adj: Dict[int, List[int]] = defaultdict(list)
    in_adj:  Dict[int, List[int]] = defaultdict(list)

    for src, tgt in zip(edges_df["source"].tolist(), edges_df["target"].tolist()):
        out_adj[src].append(tgt)
        in_adj[tgt].append(src)

    logger.info("Adjacency maps built (%d nodes with outgoing edges)", len(out_adj))
    return dict(out_adj), dict(in_adj)


def _build_timestep_index(nodes_df: pd.DataFrame) -> Dict[int, List[int]]:
    """Map timestep → list of tx_ids."""
    logger.info("Building timestep index…")
    idx: Dict[int, List[int]] = defaultdict(list)
    for tx_id, ts in zip(nodes_df.index.tolist(), nodes_df["timestep"].tolist()):
        idx[int(ts)].append(int(tx_id))
    return dict(idx)


def load_dataset() -> None:
    """
    Load all three CSV files into _store.
    Called once at application startup via FastAPI lifespan.
    """
    global _store

    if _store.loaded:
        logger.warning("Dataset already loaded — skipping.")
        return

    t_total = time.perf_counter()
    logger.info("=== Starting dataset load ===")

    # 1. Load raw data
    _store.features_df = _load_features()
    _store.classes_df  = _load_classes()
    _store.edges_df    = _load_edges()

    # 2. Build lightweight node info frame (no feature columns)
    logger.info("Building nodes_df…")
    nodes = _store.features_df[["timestep"]].copy()
    nodes = nodes.join(_store.classes_df[["label", "label_raw"]], how="left")
    nodes["label"]     = nodes["label"].fillna("unknown")
    nodes["label_raw"] = nodes["label_raw"].fillna("unknown")
    _store.nodes_df = nodes

    # 3. Adjacency
    _store.out_adj, _store.in_adj = _build_adjacency(_store.edges_df)

    # 4. Timestep index
    _store.timestep_index = _build_timestep_index(_store.nodes_df)

    # 5. All tx ids set
    _store.all_tx_ids = set(_store.nodes_df.index.tolist())

    _store.loaded = True
    elapsed = time.perf_counter() - t_total
    logger.info("=== Dataset ready in %.1fs ===", elapsed)


# ── Helper utilities (used by routers) ────────────────────────────────────────

def node_exists(tx_id: int) -> bool:
    return tx_id in _store.all_tx_ids


def get_node_row(tx_id: int) -> Optional[pd.Series]:
    if not node_exists(tx_id):
        return None
    return _store.nodes_df.loc[tx_id]


def get_feature_row(tx_id: int) -> Optional[pd.Series]:
    if not node_exists(tx_id):
        return None
    return _store.features_df.loc[tx_id]


def get_out_neighbors(tx_id: int) -> List[int]:
    return _store.out_adj.get(tx_id, [])


def get_in_neighbors(tx_id: int) -> List[int]:
    return _store.in_adj.get(tx_id, [])


def get_timestep_tx_ids(timestep: int) -> List[int]:
    return _store.timestep_index.get(timestep, [])


def bfs_subgraph(
    root: int,
    depth: int,
    max_nodes: int = 500,
) -> Tuple[List[int], List[Tuple[int, int]]]:
    """
    Breadth-first subgraph expansion from `root` up to `depth` hops.
    Returns (node_ids, edge_pairs).
    """
    visited: Set[int] = {root}
    frontier: List[int] = [root]
    edge_set: Set[Tuple[int, int]] = set()

    for _ in range(depth):
        if len(visited) >= max_nodes:
            break
        next_frontier: List[int] = []
        for node in frontier:
            for nbr in _store.out_adj.get(node, []):
                edge_set.add((node, nbr))
                if nbr not in visited and len(visited) < max_nodes:
                    visited.add(nbr)
                    next_frontier.append(nbr)
            for nbr in _store.in_adj.get(node, []):
                edge_set.add((nbr, node))
                if nbr not in visited and len(visited) < max_nodes:
                    visited.add(nbr)
                    next_frontier.append(nbr)
        frontier = next_frontier
        if not frontier:
            break

    return list(visited), list(edge_set)
