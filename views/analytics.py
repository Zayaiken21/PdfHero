"""PDF Hero — Analytics. The whole workspace in numbers: score distribution,
niche strength, trend & intent mix, platform pull, your best ideas, and
duplicate detection across everything you've saved."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, chips, full_table, keyword_cloud)
from core.duplicate_checker import find_dupe_groups
from core.projects import list_projects, load_project

inject_css()
user = st.session_state["user"]

hero("Analytics",
     "Everything you've researched, measured: where the strong scores cluster, "
     "which niches you're deepest in, what's rising, and what to build next.")

projects = list_projects(user["id"])
if not projects:
    st.info("No data yet — run any research page and the numbers appear here.")
    st.stop()

all_rows, per_project = [], []
for p in projects:
    data = load_project(user["id"], p["slug"]) or {}
    rows = data.get("rows", [])
    all_rows += rows
    per_project.append({"name": p["name"], "type": p["type"],
                        "created": p["created"], "ideas": len(rows),
                        "best": max((int(r.get("opportunity", 0)) for r in rows),
                                    default=0)})

scores = [int(r.get("opportunity", 0)) for r in all_rows]
rising = sum(1 for r in all_rows if r.get("trend_label") == "Rising")
niches = {}
for r in all_rows:
    n = r.get("niche") or r.get("category") or "General"
    niches[n] = niches.get(n, 0) + 1

m = st.columns(5)
m[0].metric("Projects", len(projects))
m[1].metric("Ideas", f"{len(all_rows):,}")
m[2].metric("Niches", len(niches))
m[3].metric("Avg score", round(sum(scores) / len(scores)) if scores else 0)
m[4].metric("Rising now", rising)

import pandas as pd

left, right = st.columns(2)
with left:
    st.markdown("##### Score distribution")
    bands = {"85+ hot": 0, "70–84 strong": 0, "55–69 viable": 0, "<55 weak": 0}
    for s in scores:
        if s >= 85:
            bands["85+ hot"] += 1
        elif s >= 70:
            bands["70–84 strong"] += 1
        elif s >= 55:
            bands["55–69 viable"] += 1
        else:
            bands["<55 weak"] += 1
    st.bar_chart(pd.DataFrame({"ideas": bands.values()}, index=list(bands)),
                 color="#38BDF8")
with right:
    st.markdown("##### Ideas per niche (top 10)")
    top_n = dict(sorted(niches.items(), key=lambda kv: -kv[1])[:10])
    st.bar_chart(pd.DataFrame({"ideas": top_n.values()}, index=list(top_n)),
                 color="#818CF8", horizontal=True)

left2, right2 = st.columns(2)
with left2:
    st.markdown("##### Trend mix")
    tmix = {}
    for r in all_rows:
        t = (r.get("trend_label") or "—").replace("Est. ", "")
        tmix[t] = tmix.get(t, 0) + 1
    st.bar_chart(pd.DataFrame({"ideas": tmix.values()}, index=list(tmix)),
                 color="#34D399")
with right2:
    st.markdown("##### Buyer-intent mix")
    imix = {}
    for r in all_rows:
        i = r.get("intent") or "—"
        imix[i] = imix.get(i, 0) + 1
    st.bar_chart(pd.DataFrame({"ideas": imix.values()}, index=list(imix)),
                 color="#FBBF24")

plat = {}
for r in all_rows:
    for p_ in r.get("platforms", []) or []:
        plat[p_] = plat.get(p_, 0) + 1
if plat:
    st.markdown("##### Where your ideas sell best")
    st.markdown(chips([f"{k} · {v}" for k, v in
                       sorted(plat.items(), key=lambda kv: -kv[1])[:8]], "accent"),
                unsafe_allow_html=True)

best = sorted(all_rows, key=lambda r: -int(r.get("opportunity", 0)))[:15]
st.markdown("##### Your 15 strongest ideas across everything")
full_table(best)
keyword_cloud([(r["keyword"], r.get("opportunity", 1)) for r in best], max_items=30)

dupes = find_dupe_groups([r.get("keyword", "") for r in all_rows])
if dupes:
    with st.expander(f"🔁 {len(dupes)} near-duplicate group(s) across projects — "
                     "keep one, retire the rest"):
        for g in dupes[:25]:
            st.markdown("- " + " ≈ ".join(g))

st.markdown("##### Per-project scoreboard")
st.dataframe(pd.DataFrame(per_project), use_container_width=True, hide_index=True)

from utils.http import SOURCE_HEALTH
if SOURCE_HEALTH:
    with st.expander("📡 Data-source health (this session)"):
        rows = [{"source": name, "ok": h.get("ok", 0), "failed": h.get("fail", 0),
                 "last error": (h.get("last_error") or "")[:60]}
                for name, h in sorted(SOURCE_HEALTH.items())]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
