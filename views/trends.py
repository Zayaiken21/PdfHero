"""PDF Hero — Trend Discovery. What's hot right now, ranked niches on the
move, and today's trending PDF opportunities. All live data, no filler."""
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
from core.opportunity_engine import detect_category
from utils.cache import cache

inject_css()
user = st.session_state["user"]

hero("Trend Discovery",
     "Live pulse: today's hot searches, which PDF niches are moving right now, "
     "and the trending phrases you can turn into products this week.")

country = country_picker("🌍 Country", key="trend_country")
run = st.button("⚡ Scan what's trending now", type="primary", key="trend_run",
                use_container_width=True)


def _hot_searches(country_name: str) -> list[str]:
    """Today's trending searches via Google Trends (cached 3h). Empty when the
    library or endpoint is unavailable — never fake."""
    pn_map = {"United States": "united_states", "United Kingdom": "united_kingdom",
              "Canada": "canada", "Australia": "australia", "India": "india",
              "Germany": "germany", "France": "france", "Brazil": "brazil",
              "Mexico": "mexico", "Italy": "italy", "Spain": "spain",
              "Netherlands": "netherlands", "New Zealand": "new_zealand",
              "Ireland": "ireland", "Philippines": "philippines",
              "South Africa": "south_africa"}
    pn = pn_map.get(country_name, "united_states")
    hit = cache.get("hot-searches", pn)
    if hit is not None:
        return hit
    out: list[str] = []
    try:
        from pytrends.request import TrendReq
        df = TrendReq(hl="en-US", tz=0, timeout=(4, 10)).trending_searches(pn=pn)
        if df is not None and not df.empty:
            out = [str(v) for v in df[df.columns[0]].tolist()[:14]]
    except Exception:
        out = []
    cache.set("hot-searches", pn, out, ttl=3 * 3600)
    return out


if run:
    # 1 · today's hot searches (real; skipped silently if source is down)
    with st.spinner("Reading today's hot searches…"):
        hot = _hot_searches(country)

    # 2 · live niche movement — real probes, real progress
    bar, update = progress_runner(len(topics.THEMES), "Measuring live niche demand")
    ranked = topics.rank_themes(country, limit=8, progress_cb=update)
    bar.progress(1.0, text="Niche demand measured")

    # 3 · trending PDF opportunities from the top-moving niche (one theme →
    #     consistent results, no category mixing)
    top_theme = ranked[0]["name"] if ranked else "Productivity & ADHD"
    queries = topics.theme_queries(top_theme, per_seed=5, max_queries=20)
    bar2, update2 = progress_runner(1, f"Harvesting {top_theme} trends")
    rows, clusters, cname = research_pipeline(
        queries, country, include_shopping=True, keep=40, trends_top=6,
        theme_label=top_theme, progress=update2)
    st.session_state["trend_result"] = {"hot": hot, "ranked": ranked,
                                        "rows": rows, "theme": top_theme,
                                        "country": cname}
    if rows:
        save_project(user["id"], f"Trends · {top_theme} ({cname})", "trends",
                     top_theme, rows)

res = st.session_state.get("trend_result")
if res:
    geo_badge(res["country"])

    if res["hot"]:
        st.markdown("#### 🔥 Hot searches today")
        marked = []
        for h in res["hot"]:
            cat = detect_category(h)["category"]
            marked.append(f"⚡ {h}" if cat != "General" else h)
        st.markdown(chips(marked), unsafe_allow_html=True)
        st.caption("⚡ = maps naturally to a sellable PDF category.")

    st.markdown("#### 📈 Niches moving right now (live demand)")
    for t in res["ranked"]:
        with st.expander(f"{t['icon']} **{t['name']}** · demand score {t['score']} · "
                         f"{t['suggestions']} live suggestions"):
            if t["sample"]:
                st.markdown(chips(t["sample"]), unsafe_allow_html=True)
            st.page_link("views/niche.py", label=f"🎯 Deep-dive {t['name']} in Niche Research",
                         use_container_width=True)

    rows = res["rows"]
    if rows:
        st.markdown(f"#### ⚡ Trending PDF opportunities · {res['theme']}")
        st.caption("All from one niche so the set stays consistent — saved to your "
                   "Projects automatically.")
        detail_expanders(rows, key_prefix="trend", limit=25)
        full_table(rows)
        keyword_cloud([(r["keyword"], r.get("opportunity", 1)) for r in rows[:40]])
        export_buttons({"slug": "trend-discovery", "rows": rows,
                        "country": res["country"]}, key_prefix="trend")
else:
    st.caption("Tap the scan — it reads live search sources only, so what you see "
               "is what people are typing today.")
