"""PDF Hero — Home. Workspace dashboard + the six things this app does."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, keyword_cloud, score_badge, geo_badge)
from core.projects import list_projects, load_project

inject_css()
user = st.session_state["user"]

hero("PDF Hero",
     "Track what's trending, rate the profitable PDF ideas, and let the AI build "
     "your product lines and bundles — all from real, live search data. Every "
     "result is unique, deduplicated, and saved privately to your workspace.")

projects = list_projects(user["id"])
total_ideas = sum(p["keywords"] for p in projects)
latest = load_project(user["id"], projects[0]["slug"]) if projects else None
best = 0
if latest and latest.get("rows"):
    best = max(int(r.get("opportunity", 0)) for r in latest["rows"])

from ai.provider import status as ai_status
from core.volume import status as vol_status
ai = ai_status()
vol = vol_status()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Projects", len(projects))
c2.metric("Ideas researched", f"{total_ideas:,}")
c3.metric("Latest best score", best if latest else "—")
c4.metric("AI provider", ai["provider"] + (" ✓" if ai["ok"] else " ✗"))
st.caption(f"Search-volume source: {vol['label']}")

st.markdown("#### What do you want to do?")
r1 = st.columns(3)
with r1[0]:
    st.page_link("views/trends.py", label="📈 Track what's trending right now",
                 use_container_width=True)
with r1[1]:
    st.page_link("views/niche.py", label="🎯 Discover the hottest niches",
                 use_container_width=True)
with r1[2]:
    st.page_link("views/keywords.py", label="🔑 Auto-find profitable keywords",
                 use_container_width=True)
r2 = st.columns(3)
with r2[0]:
    st.page_link("views/url_research.py", label="🔗 Pull the top SEO winners (or any URL)",
                 use_container_width=True)
with r2[1]:
    st.page_link("views/studio.py", label="🧠 Build listings, lines & bundles with AI",
                 use_container_width=True)
with r2[2]:
    st.page_link("views/analytics.py", label="📊 See your numbers across everything",
                 use_container_width=True)

if latest and latest.get("rows"):
    st.markdown("#### Latest project · " + latest.get("name", ""))
    if latest.get("country"):
        geo_badge(latest["country"])
    rows = latest["rows"][:10]
    left, right = st.columns([3, 2])
    with left:
        try:
            import pandas as pd
            df = pd.DataFrame({"idea": [r["keyword"] for r in rows],
                               "score": [r.get("opportunity", 0) for r in rows]})
            st.bar_chart(df.set_index("idea"), color="#38BDF8", horizontal=True)
        except Exception:
            for r in rows:
                st.write(f"{score_badge(r.get('opportunity', 0))} {r['keyword']}",
                         unsafe_allow_html=True)
    with right:
        keyword_cloud([(r["keyword"], r.get("opportunity", 1))
                       for r in latest["rows"][:30]])

    top = latest["rows"][0]
    if top.get("pdf_titles"):
        st.markdown("##### Your top idea, ready to sell")
        st.markdown(f'<div class="si-title-idea">{top["pdf_titles"][0]}</div>',
                    unsafe_allow_html=True)
else:
    st.info("Nothing saved yet. Start with **Trend Discovery** or **Niche Research** — "
            "one tap finds what people are searching right now.")
