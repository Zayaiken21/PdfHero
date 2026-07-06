"""Auto Pilot — one automatic pipeline that does everything:

  seed/niche -> keyword expansion -> multi-source suggestion harvest ->
  dedupe -> Google Trends signals -> search volume (real or est.) ->
  opportunity scoring & ranking -> niche clustering -> AI SEO listings
  for the top ideas -> saved project.

Every stage degrades gracefully and reports progress via callback:
progress_cb(stage:str, done:int, total:int, detail:str)
"""
from __future__ import annotations

import time

from scrapers import fetch_many, DEFAULT_SOURCES, SHOPPING_SOURCES
from core import trend_engine, volume, geo as geo_mod, query_forge
from core.duplicate_checker import dedupe_rows
from core.opportunity_engine import enrich_rows
from core.projects import save_project
from nlp.clustering import cluster_keywords


def _noop(stage, done, total, detail=""):
    pass


def run_autopilot(user_id: int = 0, seed: str = "", audience: str = "", mode: str = "seed",
                  country: str = "United States",
                  sources: list[str] | None = None, include_shopping: bool = True,
                  max_queries: int = 40, top_keywords: int = 60,
                  listings_to_generate: int = 3, generate_ai: bool = True,
                  progress_cb=None) -> dict:
    """Run the full pipeline. mode: 'seed' (expand one keyword) or
    'auto' (discover across PDF categories). Returns the saved project dict
    plus 'clusters', 'log', and 'ai_errors'."""
    cb = progress_cb or _noop
    log: list[str] = []
    t0 = time.time()

    # ── Stage 1: build query list ────────────────────────────────────────
    cb("Planning queries", 0, 1, mode)
    if mode == "auto" or not seed.strip():
        queries, topics = query_forge.discovery_queries(count=6, audience=audience,
                                                        depth="standard")
        label_seed = audience or "auto discovery"
    else:
        queries = query_forge.reformulate(seed, depth="deep")
        label_seed = seed
    queries = queries[:max_queries]
    log.append(f"{len(queries)} expansion queries built")
    cb("Planning queries", 1, 1, f"{len(queries)} queries")

    # ── Stage 2: harvest suggestions from public sources ─────────────────
    g = geo_mod.resolve(country)
    src = list(sources or DEFAULT_SOURCES)
    if include_shopping:
        src += [s for s in SHOPPING_SOURCES if s not in src]

    def harvest_cb(done, total, detail=""):
        cb("Harvesting search suggestions", done, total, detail)

    rows = fetch_many(queries, sources=src, progress=harvest_cb,
                      lang=g["hl"], country=g["gl"])
    log.append(f"{len(rows)} raw keywords from {len(src)} sources")

    # ── Stage 3: dedupe + rank prep ──────────────────────────────────────
    cb("Removing duplicates", 0, 1, "")
    rows = dedupe_rows(rows)
    rows.sort(key=lambda r: (-r.get("source_count", 0), -r.get("frequency", 0)))
    rows = rows[:top_keywords]
    log.append(f"{len(rows)} unique keywords kept")
    cb("Removing duplicates", 1, 1, f"{len(rows)} unique")

    # ── Stage 4: trend signals (real for the top slice) ──────────────────
    def trend_cb(done, total, detail=""):
        cb("Reading Google Trends", done, total, detail)
    rows = trend_engine.attach_trends(rows, top_n=8, geo=g["trends_geo"],
                                     country_name=g["name"], progress_cb=trend_cb)

    # ── Stage 5: search volume ───────────────────────────────────────────
    def vol_cb(done, total, detail=""):
        cb("Fetching search volume", done, total, detail)
    rows = volume.get_volumes(rows, progress_cb=vol_cb)
    vstat = volume.status()
    log.append(f"Volume source: {vstat['label']}")

    # ── Stage 6: opportunity scoring + ranking ───────────────────────────
    cb("Scoring opportunities", 0, 1, "")
    rows = enrich_rows(rows)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    cb("Scoring opportunities", 1, 1, f"top score {rows[0]['opportunity'] if rows else 0}")

    # ── Stage 7: niche clustering ────────────────────────────────────────
    cb("Clustering niches", 0, 1, "")
    clusters = cluster_keywords([r["keyword"] for r in rows])
    name_by_kw = {}
    for cl in clusters:
        for kw in cl.get("keywords", []):
            name_by_kw[kw] = cl.get("label", "General")
    for row in rows:
        row["niche"] = name_by_kw.get(row["keyword"], row.get("category", "General"))
    cb("Clustering niches", 1, 1, f"{len(clusters)} niches")
    log.append(f"{len(clusters)} niche clusters identified")

    # ── Stage 8: AI SEO listings for the top ideas ───────────────────────
    listing, ai_errors = {}, []
    if generate_ai and rows:
        from ai import provider as ai_provider
        from ai.prompt_templates import SYSTEM_SEO, build_listing_prompt
        stat = ai_provider.status()
        if not stat["ok"]:
            ai_errors.append(f"AI provider '{stat['provider']}' unavailable: {stat['detail']}. "
                             "Research results are complete — connect a provider in Settings to generate listings.")
        else:
            targets = rows[:max(1, listings_to_generate)]
            listings = {}
            related = [r["keyword"] for r in rows[:25]]
            for i, row in enumerate(targets):
                cb("Generating AI listings", i, len(targets), row["keyword"])
                try:
                    ctx = {"related": related, "category": row.get("category"),
                           "intent": row.get("intent"),
                           "volume_label": row.get("volume_label"),
                           "audience": audience}
                    listings[row["keyword"]] = ai_provider.generate_json(
                        build_listing_prompt(row["keyword"], ctx), system=SYSTEM_SEO)
                except Exception as exc:
                    ai_errors.append(f"{row['keyword']}: {exc}")
            cb("Generating AI listings", len(targets), len(targets), "done")
            if listings:
                first = next(iter(listings))
                listing = {"primary_keyword": first, "primary": listings[first],
                           "all": listings}
                log.append(f"{len(listings)} AI listing(s) generated")

    # ── Stage 9: save project ────────────────────────────────────────────
    name = f"AutoPilot · {label_seed} · {time.strftime('%b %d %H:%M')}"
    project = save_project(user_id, name, "autopilot", label_seed, rows, listing=listing,
                           notes="; ".join(log))
    project["country"] = g["name"]
    project["clusters"] = clusters
    project["log"] = log
    project["ai_errors"] = ai_errors
    project["elapsed"] = round(time.time() - t0, 1)
    cb("Complete", 1, 1, f"{project['elapsed']}s")
    return project
