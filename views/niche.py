"""PDF Hero — Niche Research. Auto-discovers which niches are popular from
live search demand, then deep-dives ONE niche at a time so every result set
stays consistent (pets stay with pets, money stays with money)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, chips, country_picker, detail_expanders,
                      export_buttons, full_table, geo_badge, keyword_cloud,
                      progress_runner)
from core import topics
from core.pipeline import research_pipeline
from core.projects import save_project

inject_css()
user = st.session_state["user"]

hero("Niche Research",
     "One tap ranks every PDF niche by what people are searching right now. "
     "Deep-dive any of them for a full, consistent set of rated ideas — "
     "or type a niche of your own.")

country = country_picker("🌍 Country", key="niche_country")

c1, c2 = st.columns([1, 1])
auto = c1.button("🎯 Discover popular niches", type="primary", key="niche_auto",
                 use_container_width=True)
custom = c2.text_input("…or type your own niche", placeholder="e.g. homeschool moms",
                       key="niche_custom", label_visibility="collapsed")
go_custom = c2.button("Research this niche", key="niche_custom_btn",
                      use_container_width=True)

if auto:
    bar, update = progress_runner(len(topics.THEMES), "Measuring live demand per niche")
    ranked = topics.rank_themes(country, limit=len(topics.THEMES), progress_cb=update)
    bar.progress(1.0, text="Done — ranked by live search suggestions")
    st.session_state["niche_ranked"] = {"ranked": ranked, "country": country}


def _deep_dive(theme: str, cname: str):
    queries = topics.theme_queries(theme, per_seed=6, max_queries=26)
    bar, update = progress_runner(1, f"Harvesting {theme}")
    rows, clusters, resolved = research_pipeline(
        queries, cname, include_shopping=True, keep=70, trends_top=6,
        theme_label=theme, progress=update)
    if rows:
        save_project(user["id"], f"Niche · {theme} ({resolved})", "niche", theme, rows)
    st.session_state["niche_result"] = {"rows": rows, "theme": theme,
                                        "country": resolved}


ranked_state = st.session_state.get("niche_ranked")
if ranked_state:
    geo_badge(ranked_state["country"])
    st.markdown("#### Niches ranked by live demand")
    st.caption("Demand = how many suggestions public search engines return for the "
               "niche right now, across sources. Cached briefly, so re-scans are instant.")
    for t in ranked_state["ranked"]:
        head = (f"#{t['rank']} {t['icon']} **{t['name']}** · demand {t['score']} · "
                f"{t['suggestions']} live suggestions")
        with st.expander(head, expanded=t["rank"] <= 2):
            if t["sample"]:
                st.markdown("**People are typing:** " + chips(t["sample"], "accent"),
                            unsafe_allow_html=True)
            if st.button(f"🔬 Deep-dive {t['name']}", key=f"dd_{t['name']}",
                         use_container_width=True):
                _deep_dive(t["name"], ranked_state["country"])

if go_custom and custom.strip():
    from core.query_forge import reformulate
    base = custom.strip().lower()
    queries = reformulate(base, depth="standard")
    queries += [f"{base} {m}" for m in
                ("planner", "printable", "checklist", "worksheet", "tracker", "journal")]
    queries = list(dict.fromkeys(queries))
    bar, update = progress_runner(1, f"Harvesting “{base}”")
    rows, clusters, resolved = research_pipeline(
        queries, country, include_shopping=True, keep=70, trends_top=6,
        theme_label=topics.match_theme(base) or base.title(), progress=update)
    if rows:
        save_project(user["id"], f"Niche · {base} ({resolved})", "niche", base, rows)
    st.session_state["niche_result"] = {"rows": rows, "theme": base.title(),
                                        "country": resolved}

res = st.session_state.get("niche_result")
if res and res.get("rows"):
    rows = res["rows"]
    st.markdown(f"### 🔬 {res['theme']} — {len(rows)} rated ideas")
    geo_badge(res["country"])
    m = st.columns(3)
    m[0].metric("Top score", rows[0]["opportunity"])
    m[1].metric("Rising", sum(1 for r in rows if r.get("trend_label") == "Rising"))
    m[2].metric("Buyer-intent", sum(1 for r in rows
                                    if r.get("intent") in ("transactional", "commercial")))
    st.caption("Saved to Projects. Every idea below belongs to this one niche — "
               "no category mixing.")
    detail_expanders(rows, key_prefix="nr", limit=35)
    full_table(rows)
    keyword_cloud([(r["keyword"], r.get("opportunity", 1)) for r in rows[:40]])
    export_buttons({"slug": "niche-research", "rows": rows,
                    "country": res["country"]}, key_prefix="nr")
