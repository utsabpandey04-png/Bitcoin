"""
routers/stats.py — Summary statistics endpoints.
"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends

from backend.config import CLASS_MAP, FEATURE_NAMES
from backend.data.loader import DataStore, get_store
from backend.schemas.models import (
    ClassCount,
    FeatureStat,
    FeatureStatsResponse,
    OverviewStats,
    TimestepStats,
    TimestepStatsResponse,
)

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get(
    "/overview",
    response_model=OverviewStats,
    summary="Dataset overview",
    description="Returns total transaction count, edge count, number of timesteps, and class distribution.",
)
def overview(store: Annotated[DataStore, Depends(get_store)]):
    df    = store.nodes_df
    total = len(df)

    counts = df["label"].value_counts().to_dict()
    class_dist: List[ClassCount] = []
    raw_map = {v: k for k, v in CLASS_MAP.items()}  # label → label_raw

    for label in ["illicit", "licit", "unknown"]:
        cnt = counts.get(label, 0)
        class_dist.append(
            ClassCount(
                label=label,
                label_raw=raw_map.get(label, "unknown"),
                count=cnt,
                percentage=round(cnt / total * 100, 4) if total else 0.0,
            )
        )

    return OverviewStats(
        total_transactions=total,
        total_edges=len(store.edges_df),
        total_timesteps=int(df["timestep"].nunique()),
        class_distribution=class_dist,
    )


@router.get(
    "/timesteps",
    response_model=TimestepStatsResponse,
    summary="Per-timestep breakdown",
    description="For each of the 49 timesteps, returns illicit / licit / unknown transaction counts and percentages.",
)
def timestep_stats(store: Annotated[DataStore, Depends(get_store)]):
    df = store.nodes_df

    grouped = (
        df.groupby(["timestep", "label"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Ensure all columns exist even if some labels are absent in a timestep
    for col in ["illicit", "licit", "unknown"]:
        if col not in grouped.columns:
            grouped[col] = 0

    result: List[TimestepStats] = []
    for _, row in grouped.iterrows():
        illicit = int(row.get("illicit", 0))
        licit   = int(row.get("licit",   0))
        unknown = int(row.get("unknown", 0))
        total   = illicit + licit + unknown
        pct     = lambda n: round(n / total * 100, 4) if total else 0.0

        result.append(
            TimestepStats(
                timestep=int(row["timestep"]),
                total=total,
                illicit=illicit,
                licit=licit,
                unknown=unknown,
                illicit_pct=pct(illicit),
                licit_pct=pct(licit),
                unknown_pct=pct(unknown),
            )
        )

    result.sort(key=lambda x: x.timestep)
    return TimestepStatsResponse(data=result)


@router.get(
    "/class-distribution",
    summary="Class distribution (chart-ready)",
    description="Returns illicit / licit / unknown counts — suitable for pie/bar charts.",
)
def class_distribution(store: Annotated[DataStore, Depends(get_store)]):
    df     = store.nodes_df
    total  = len(df)
    counts = df["label"].value_counts().to_dict()
    raw_map = {v: k for k, v in CLASS_MAP.items()}

    return {
        "total": total,
        "classes": [
            {
                "label": label,
                "label_raw": raw_map.get(label, "unknown"),
                "count": counts.get(label, 0),
                "percentage": round(counts.get(label, 0) / total * 100, 4) if total else 0.0,
            }
            for label in ["illicit", "licit", "unknown"]
        ],
    }


@router.get(
    "/features",
    response_model=FeatureStatsResponse,
    summary="Feature statistics",
    description=(
        "Descriptive statistics (mean, std, min, max, p25, p50, p75) "
        "for all 166 anonymised features across the entire dataset."
    ),
)
def feature_stats(store: Annotated[DataStore, Depends(get_store)]):
    desc = store.features_df[FEATURE_NAMES].describe(percentiles=[0.25, 0.5, 0.75])

    stats: List[FeatureStat] = []
    for feat in FEATURE_NAMES:
        col = desc[feat]
        stats.append(
            FeatureStat(
                feature=feat,
                mean=round(float(col["mean"]), 6),
                std=round(float(col["std"]),  6),
                min=round(float(col["min"]),  6),
                max=round(float(col["max"]),  6),
                p25=round(float(col["25%"]),  6),
                p50=round(float(col["50%"]),  6),
                p75=round(float(col["75%"]),  6),
            )
        )

    return FeatureStatsResponse(features=stats)
