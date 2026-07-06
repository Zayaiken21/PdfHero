"""PDF Hero — one shared research pipeline for every page.

Real work, real progress: the bar advances only when a fetch actually
completes, and once results are in session/projects they render instantly
with no artificial loading.
"""
from __future__ import annotations

from core import geo as geo_mod, trend_engine, volume
from core.duplicate_checker import dedupe_rows
from core.opportunity_engine import enrich_rows
from nlp.clustering import cluster_keywords
from scrapers import fetch_many, DEFAULT_SOURCES, SHOPPING_SOURCES


def research_pipeline(queries: list[str], country: str,
                      include_shopping: bool = True, keep: int = 80,
                      do_cluster: bool = True, trends_top: int = 6,
                      theme_label: str = "", progress=None) -> tuple[list[dict], list[dict], str]:
    """queries -> ranked, deduped, scored rows.

    theme_label: when set, every row is pinned to that one niche so a run never
    mixes categories.
    Returns (rows, clusters, country_name).
    """
    g = geo_mod.resolve(country)
    src = list(DEFAULT_SOURCES) + (list(SHOPPING_SOURCES) if include_shopping else [])

    rows = fetch_many(queries, sources=src, progress=progress,
                      lang=g["hl"], country=g["gl"])
    rows = dedupe_rows(rows)
    rows.sort(key=lambda r: (-r.get("source_count", 0), -r.get("frequency", 0)))
    rows = rows[:keep]

    rows = trend_engine.attach_trends(rows, top_n=trends_top, geo=g["trends_geo"],
                                      country_name=g["name"])
    rows = volume.get_volumes(rows)
    rows = enrich_rows(rows)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    clusters: list[dict] = []
    if theme_label:
        for r in rows:
            r["niche"] = theme_label
        clusters = [{"label": theme_label, "keywords": [r["keyword"] for r in rows],
                     "size": len(rows)}]
    elif do_cluster:
        clusters = cluster_keywords([r["keyword"] for r in rows])
        name_by_kw = {kw: cl.get("label", "General")
                      for cl in clusters for kw in cl.get("keywords", [])}
        for r in rows:
            r["niche"] = name_by_kw.get(r["keyword"], r.get("category", "General"))
    return rows, clusters, g["name"]


def group_rows_by_niche(rows: list[dict]) -> dict[str, list[dict]]:
    """Ordered {niche: rows} so pages can render one clean section per niche."""
    groups: dict[str, list[dict]] = {}
    for r in rows or []:
        groups.setdefault(r.get("niche") or r.get("category") or "General", []).append(r)
    return dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))
