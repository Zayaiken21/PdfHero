"""PDF Hero — Projects. Everything you've saved, structured: grouped by type,
searchable, sortable, with full detail, exports, and clean deletion —
one project, a selected set, or everything at once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, detail_expanders, export_buttons,
                      full_table, geo_badge, keyword_cloud)
from core.projects import (delete_all_projects, delete_project, list_projects,
                           load_project)

inject_css()
user = st.session_state["user"]

hero("Projects",
     "Your private library — every run, structured by type. Open any project "
     "for the full breakdown, export it, or clear out what you're done with.")

projects = list_projects(user["id"])
if not projects:
    st.info("Nothing saved yet. Every research run saves here automatically.")
    st.stop()

TYPE_LABELS = {"trends": "📈 Trend Discovery", "niche": "🎯 Niche Research",
               "keywords": "🔑 Keyword Research", "url": "🔗 URL Research",
               "listing": "✨ Listings", "product-line": "🧱 Product Lines",
               "bundle": "📦 Bundles", "autopilot": "🚀 Auto runs"}

# ── toolbar ──────────────────────────────────────────────────────────
t1, t2, t3 = st.columns([2, 1.4, 1.2])
query = t1.text_input("Search projects", placeholder="name or seed…",
                      key="pj_search")
type_filter = t2.multiselect("Type", sorted({p["type"] for p in projects}),
                             key="pj_types")
sort_by = t3.selectbox("Sort", ["Newest", "Most ideas", "Name"], key="pj_sort")

view = [p for p in projects
        if (not query or query.lower() in p["name"].lower())
        and (not type_filter or p["type"] in type_filter)]
if sort_by == "Most ideas":
    view.sort(key=lambda p: -p["keywords"])
elif sort_by == "Name":
    view.sort(key=lambda p: p["name"].lower())

m = st.columns(3)
m[0].metric("Projects", len(projects))
m[1].metric("Showing", len(view))
m[2].metric("Total ideas", f"{sum(p['keywords'] for p in projects):,}")

# ── bulk deletion ────────────────────────────────────────────────────
with st.expander("🗑️ Delete projects (one, several, or all)"):
    sel = st.multiselect("Pick projects to delete",
                         [p["name"] for p in view], key="pj_del_sel")
    ok_sel = st.checkbox("I understand the selected projects will be permanently "
                         "deleted", key="pj_del_ok")
    if st.button(f"Delete {len(sel)} selected", key="pj_del_btn",
                 disabled=not (sel and ok_sel)):
        by_name = {p["name"]: p["slug"] for p in projects}
        for name in sel:
            delete_project(user["id"], by_name[name])
        st.toast(f"Deleted {len(sel)} project(s)", icon="🗑️")
        st.rerun()
    st.divider()
    st.markdown("**Delete ALL projects in this workspace**")
    typed = st.text_input(f"Type your workspace name (`{user['username']}`) to confirm",
                          key="pj_nuke_typed")
    if st.button("Delete ALL my projects", key="pj_nuke",
                 disabled=typed.strip().lower() != user["username"]):
        n = delete_all_projects(user["id"])
        st.toast(f"Deleted all {n} project(s)", icon="🗑️")
        st.rerun()

# ── structured listing, grouped by type ──────────────────────────────
groups: dict[str, list[dict]] = {}
for p in view:
    groups.setdefault(p["type"] or "other", []).append(p)

for ptype, plist in groups.items():
    st.markdown(f"### {TYPE_LABELS.get(ptype, ptype.title())} · {len(plist)}")
    for p in plist:
        flag = " · ✨ listing" if p["has_listing"] else ""
        with st.expander(f"**{p['name']}** — {p['keywords']} ideas · "
                         f"{p['created']}{flag}"):
            data = load_project(user["id"], p["slug"])
            if not data:
                st.error("Could not load this project.")
                continue
            meta = st.columns([1, 1, 2])
            meta[0].metric("Ideas", p["keywords"])
            rows = data.get("rows", [])
            best = max((int(r.get("opportunity", 0)) for r in rows), default=0)
            meta[1].metric("Best score", best)
            with meta[2]:
                if data.get("country"):
                    geo_badge(data["country"])
                if data.get("seed"):
                    st.caption(f"Seed: {data['seed']}")
            if rows:
                mode = st.radio("View", ["Full detail", "Table", "Cloud"],
                                horizontal=True, key=f"pj_v_{p['slug']}")
                if mode == "Full detail":
                    detail_expanders(rows, key_prefix=f"pj_{p['slug']}", limit=25)
                elif mode == "Table":
                    full_table(rows[:80])
                else:
                    keyword_cloud([(r["keyword"], r.get("opportunity", 1))
                                   for r in rows[:40]])
            listing = (data.get("listing") or {}).get("primary")
            if listing:
                st.markdown("**Listing titles:** "
                            + " · ".join(listing.get("seo_titles", [])[:3]))
            export_buttons(data, key_prefix=f"pj_{p['slug']}")
            confirm = st.checkbox("Confirm delete", key=f"pj_c_{p['slug']}")
            if st.button("🗑️ Delete this project", key=f"pj_d_{p['slug']}",
                         disabled=not confirm):
                delete_project(user["id"], p["slug"])
                st.rerun()
