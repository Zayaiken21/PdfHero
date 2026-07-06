"""PDF Hero — Keyword Research. Fully automatic: press Run and it finds
profitable keywords by itself from the strongest live niches — nothing to
type. Add an optional focus word only if you want to steer it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, country_picker, detail_expanders,
                      export_buttons, full_table, geo_badge, keyword_cloud,
                      progress_runner)
from core import topics
from core.pipeline import research_pipeline, group_rows_by_niche
from core.projects import save_project
from core.query_forge import reformulate

inject_css()
user = st.session_state["user"]

hero("Keyword Research",
     "Zero typing needed. Run it and PDF Hero pulls live keywords from the "
     "top-demand niches, dedupes them, rates every one, and groups them by "
     "niche so nothing gets jumbled together.")

country = country_picker("🌍 Country", key="kw_country")
focus = st.text_input("Focus (optional — leave empty for full auto)",
                      placeholder="e.g. wedding planner", key="kw_focus")
run = st.button("🔑 Auto-find keywords", type="primary", key="kw_run",
                use_container_width=True)

if run:
    if focus.strip():
        seed = focus.strip().lower()
        queries = reformulate(seed, depth="deep")
        bar, update = progress_runner(1, f"Harvesting “{seed}”")
        rows, clusters, cname = research_pipeline(
            queries, country, include_shopping=True, keep=90, trends_top=6,
            progress=update)
        label = f"Keywords · {seed}"
    else:
        # pick the strongest live niches, then harvest each ON ITS OWN so the
        # groups stay consistent
        bar, update = progress_runner(len(topics.THEMES), "Ranking live niches")
        ranked = topics.rank_themes(country, limit=3, progress_cb=update)
        bar.progress(1.0, text="Top niches locked in")
        rows, cname = [], country
        for t in ranked:
            queries = topics.theme_queries(t["name"], per_seed=4, max_queries=14)
            bar2, update2 = progress_runner(1, f"Harvesting {t['name']}")
            part, _, cname = research_pipeline(
                queries, country, include_shopping=True, keep=30, trends_top=4,
                theme_label=t["name"], progress=update2)
            rows += part
        rows.sort(key=lambda r: -int(r.get("opportunity", 0)))
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        label = "Keywords · Auto"
    if rows:
        save_project(user["id"], f"{label} ({cname})", "keywords",
                     focus.strip() or "auto", rows)
    st.session_state["kw_result"] = {"rows": rows, "country": cname,
                                     "label": label}

res = st.session_state.get("kw_result")
if res and res.get("rows"):
    rows = res["rows"]
    st.markdown(f"### {res['label']} — {len(rows)} unique keywords")
    geo_badge(res["country"])
    m = st.columns(3)
    m[0].metric("Top score", rows[0]["opportunity"])
    m[1].metric("Rising", sum(1 for r in rows if r.get("trend_label") == "Rising"))
    m[2].metric("Niches", len({r.get('niche') for r in rows}))
    st.caption("Saved to Projects · grouped by niche below, so every section is "
               "one consistent category.")

    for niche, part in group_rows_by_niche(rows).items():
        with st.expander(f"**{niche}** · {len(part)} keywords", expanded=False):
            detail_expanders(part, key_prefix=f"kwg_{niche[:8]}", limit=20)

    st.markdown("##### Full ranked table")
    full_table(rows)
    keyword_cloud([(r["keyword"], r.get("opportunity", 1)) for r in rows[:45]])
    export_buttons({"slug": "keyword-research", "rows": rows,
                    "country": res["country"]}, key_prefix="kw")
else:
    st.caption("Everything here comes from live autocomplete across Google, Bing, "
               "DuckDuckGo, YouTube and the marketplaces — real phrases people are "
               "typing, never invented.")
