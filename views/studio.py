"""PDF Hero — AI Studio. One page, three builders (the old AI Generator and
Product Line Builder merged, plus the new Bundle Business):

  ✨ Listing — a complete marketplace listing for any idea
  🧱 Product Line — a free→core→flagship ladder for one niche
  📦 Bundle Business — turn your saved projects into a sellable bundle

Every builder works with no AI key via the template engine; connecting a
provider in Settings upgrades the copy automatically."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, chips, detail_expanders, export_buttons,
                      full_table)
from core import topics
from core.bundle_forge import (ai_polish_bundle, build_bundle, build_product_line,
                               bundle_to_rows)
from core.projects import list_projects, load_project, save_project
from core.title_forge import forge
from ai import provider as ai_provider

inject_css()
user = st.session_state["user"]

hero("AI Studio",
     "Listings, product lines, and whole bundle businesses — built from the "
     "real search data in your projects. Works instantly with the template "
     "engine; add an AI provider in Settings and the copy levels up.")

ai = ai_provider.status()
st.caption(f"Engine: **{'template + ' + ai['provider'] if ai['ok'] else 'template'}**"
           f"{'' if ai['ok'] else ' · connect an AI provider in Settings for the upgraded copy'}")

projects = list_projects(user["id"])
proj_names = {p["name"]: p["slug"] for p in projects}

tab_listing, tab_line, tab_bundle = st.tabs(
    ["✨ Listing", "🧱 Product Line", "📦 Bundle Business"])


# ── ✨ Listing generator ─────────────────────────────────────────────
with tab_listing:
    st.caption("A full marketplace listing — titles, description, tags per "
               "platform — for one idea.")
    src = st.radio("Idea source", ["From a project", "Type a keyword"],
                   horizontal=True, key="ls_src")
    keyword, related = "", []
    if src == "From a project" and proj_names:
        pick = st.selectbox("Project", list(proj_names), key="ls_proj")
        data = load_project(user["id"], proj_names[pick]) or {}
        rows = data.get("rows", [])
        if rows:
            kw_opts = [r["keyword"] for r in rows[:60]]
            keyword = st.selectbox("Idea", kw_opts, key="ls_kw")
            related = kw_opts[:25]
    elif src == "From a project":
        st.info("No projects yet — run any research page first, or type a keyword.")
    if src == "Type a keyword":
        keyword = st.text_input("Keyword", placeholder="e.g. adhd daily planner",
                                key="ls_manual")

    if st.button("✨ Generate listing", type="primary", key="ls_go",
                 use_container_width=True) and (keyword or "").strip():
        keyword = keyword.strip()
        listing, engine_note = None, ""
        if ai["ok"]:
            try:
                from ai.prompt_templates import SYSTEM_SEO, build_listing_prompt
                with st.spinner(f"{ai['provider']} is writing the listing…"):
                    listing = ai_provider.generate_json(
                        build_listing_prompt(keyword, {"related": related}),
                        system=SYSTEM_SEO)
                engine_note = f"AI listing · {ai['provider']}"
            except Exception as exc:
                st.warning(f"AI call failed ({exc.__class__.__name__}) — using the "
                           "template engine instead.")
        if listing is None:
            forged = forge(keyword, related=related)
            tags = sorted({w for r in related for w in r.split() if len(w) > 3})[:25]
            tags = list(dict.fromkeys(
                [t.lower() for t in tags] +
                [keyword.lower(), "printable", "pdf", "instant download",
                 "digital download"]))[:35]
            listing = {"seo_titles": forged["pdf_titles"],
                       "short_description": forged["pdf_description"][:200],
                       "long_description": forged["pdf_description"],
                       "features": forged["whats_inside"],
                       "tags": tags}
            engine_note = "Template engine"
        st.session_state["ls_result"] = {"keyword": keyword, "listing": listing,
                                         "note": engine_note}

    lres = st.session_state.get("ls_result")
    if lres:
        listing = lres["listing"]
        st.success(f"**{lres['keyword']}** · {lres['note']}")
        for t in (listing.get("seo_titles") or [])[:5]:
            st.markdown(f'<div class="si-title-idea">{t}</div>', unsafe_allow_html=True)
        if listing.get("short_description"):
            st.caption(listing["short_description"])
        if listing.get("long_description"):
            st.write(listing["long_description"])
        feats = listing.get("features") or []
        if feats:
            st.markdown("**Inside:** " + ", ".join(str(f) for f in feats[:10]))
        if listing.get("tags"):
            st.markdown("**Tags:** " + chips(listing["tags"][:30]),
                        unsafe_allow_html=True)
        try:
            from core.scoring import score_all_platforms
            scores = score_all_platforms(listing, lres["keyword"])
            st.markdown("**Platform readiness:** " + "  ".join(
                f"{p.title()} {s['score']}/100" for p, s in scores.items()))
        except Exception:
            pass
        if st.button("💾 Save listing as a project", key="ls_save",
                     use_container_width=True):
            row = {"rank": 1, "keyword": lres["keyword"],
                   "pdf_titles": (listing.get("seo_titles") or [""])[:3],
                   "pdf_description": listing.get("long_description", ""),
                   "product_type": "Listing", "opportunity": 0,
                   "category": "General", "platforms": [], "sources": [],
                   "source_count": 0, "intent": "transactional"}
            save_project(user["id"], f"Listing · {lres['keyword']}", "listing",
                         lres["keyword"], [row],
                         listing={"primary_keyword": lres["keyword"],
                                  "primary": listing,
                                  "all": {lres["keyword"]: listing}})
            st.toast("Saved to Projects", icon="💾")


# ── 🧱 Product Line builder ──────────────────────────────────────────
with tab_line:
    st.caption("A pricing ladder for one niche: free lead magnet → core PDFs → "
               "flagship bundle. Uses your saved rows when you have them.")
    theme = st.selectbox("Niche", topics.theme_names(), key="pl_theme")
    source_rows = []
    for p in projects:
        data = load_project(user["id"], p["slug"]) or {}
        source_rows += [r for r in data.get("rows", [])
                        if (r.get("niche") or r.get("category", "")) == theme]
    if not source_rows:
        st.caption("No saved rows for this niche yet — a quick live scan will fill it.")
    if st.button("🧱 Build the product line", type="primary", key="pl_go",
                 use_container_width=True):
        rows = source_rows
        if not rows:
            from core.pipeline import research_pipeline
            from utils.ui import progress_runner
            queries = topics.theme_queries(theme, per_seed=4, max_queries=14)
            bar, update = progress_runner(1, f"Quick scan · {theme}")
            rows, _, _ = research_pipeline(
                queries, st.session_state.get("country", "United States"),
                include_shopping=True, keep=25, trends_top=4,
                theme_label=theme, progress=update)
        line = build_product_line(theme, rows)
        st.session_state["pl_result"] = line

    line = st.session_state.get("pl_result")
    if line:
        st.markdown(f"### {line['line_name']}")
        if line.get("lead_magnet"):
            lm = line["lead_magnet"]
            st.markdown(f'<div class="si-card"><h4>🎁 Lead magnet — {lm["price"]}</h4>'
                        f'<div class="si-title-idea">{lm["title"]}</div>'
                        f'<div class="si-meta">{lm["pitch"]}</div></div>',
                        unsafe_allow_html=True)
        for cp in line.get("core_products", []):
            st.markdown(f'<div class="si-card"><h4>📄 Core · {cp["price"]} · '
                        f'score {cp["score"]}</h4>'
                        f'<div class="si-title-idea">{cp["title"]}</div>'
                        f'<div class="si-meta">{cp["category"]} · built on '
                        f'“{cp["keyword"]}”</div></div>',
                        unsafe_allow_html=True)
        fb = line.get("flagship_bundle", {})
        st.markdown(f'<div class="si-card"><h4>👑 Flagship — {fb.get("price","")} '
                    f'({fb.get("anchor","")})</h4>'
                    f'<div class="si-title-idea">{fb.get("title","")}</div>'
                    f'<div class="si-meta">Contains: '
                    f'{", ".join(fb.get("contains", []))}</div></div>',
                    unsafe_allow_html=True)
        st.markdown("**Pricing ladder:** " + " → ".join(line.get("pricing_ladder", [])))
        st.markdown("**Launch order:** " + " → ".join(line.get("launch_order", [])))
        if st.button("💾 Save product line", key="pl_save", use_container_width=True):
            rows = []
            for i, cp in enumerate(line.get("core_products", []), 1):
                rows.append({"rank": i, "keyword": cp["keyword"],
                             "pdf_titles": [cp["title"]],
                             "pdf_description": f"Part of {line['line_name']}",
                             "product_type": "Product line item",
                             "opportunity": cp["score"], "category": cp["category"],
                             "niche": line["theme"], "platforms": [],
                             "sources": [], "source_count": 0,
                             "intent": "transactional"})
            save_project(user["id"], f"Line · {line['line_name']}", "product-line",
                         line["theme"], rows, notes=str(line))
            st.toast("Saved to Projects", icon="💾")


# ── 📦 Bundle Business builder ───────────────────────────────────────
with tab_bundle:
    st.caption("Pick projects → PDF Hero pulls their strongest non-duplicate "
               "ideas and builds the whole bundle business: name, contents, "
               "pricing, platform plan, launch checklist, listing.")
    if not projects:
        st.info("No projects yet — run Trend Discovery, Niche Research, or Keyword "
                "Research first, then come back to bundle what you found.")
    else:
        picks = st.multiselect("Projects to bundle from", list(proj_names),
                               default=list(proj_names)[:1], key="bb_picks")
        max_items = st.slider("PDFs in the bundle", 4, 12, 8, key="bb_max")
        use_ai = st.checkbox(f"Polish with {ai['provider']}", value=ai["ok"],
                             disabled=not ai["ok"], key="bb_ai")
        if st.button("📦 Build my bundle business", type="primary", key="bb_go",
                     use_container_width=True) and picks:
            rows = []
            for name in picks:
                data = load_project(user["id"], proj_names[name]) or {}
                rows += data.get("rows", [])
            if not rows:
                st.error("Those projects have no rows — run a research page first.")
            else:
                with st.spinner("Assembling the bundle…"):
                    bundle = build_bundle(rows, picks, max_items=max_items,
                                          workspace=user["username"])
                    note = ""
                    if use_ai:
                        related = [r.get("keyword", "") for r in rows[:20]]
                        bundle, note = ai_polish_bundle(bundle, related)
                st.session_state["bb_result"] = bundle
                if note:
                    st.caption(note)

    bundle = st.session_state.get("bb_result")
    if bundle:
        st.markdown(f"### 📦 {bundle['name']}")
        st.caption(f"Engine: {bundle.get('engine','template')} · built "
                   f"{bundle.get('created','')}")
        alt = bundle.get("name_options", [])[1:]
        if alt:
            st.markdown("**Alternate names:** " + " · ".join(alt))
        m = st.columns(4)
        m[0].metric("PDFs inside", bundle["item_count"])
        m[1].metric("Bundle price", f"${bundle['price']:.2f}")
        m[2].metric("Separate value", f"${bundle['anchor_value']:.2f}")
        m[3].metric("Theme", bundle["theme"])

        st.markdown("#### What's inside (grouped)")
        for cat, titles in bundle.get("grouped_contents", {}).items():
            with st.expander(f"**{cat}** · {len(titles)}"):
                for t in titles:
                    st.markdown(f'<div class="si-title-idea">{t}</div>',
                                unsafe_allow_html=True)

        st.markdown("#### Sales description")
        st.write(bundle.get("description", ""))
        st.markdown("**Platforms:** " + chips(bundle.get("platforms", []), "accent"),
                    unsafe_allow_html=True)
        st.markdown("**Tags:** " + chips(bundle.get("tags", [])[:30]),
                    unsafe_allow_html=True)

        st.markdown("#### Launch checklist")
        for i, step in enumerate(bundle.get("launch_checklist", []), 1):
            st.markdown(f"{i}. {step}")

        rows = bundle_to_rows(bundle)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Save bundle as a project", key="bb_save",
                         use_container_width=True):
                save_project(user["id"], f"Bundle · {bundle['theme']} · "
                             f"{time.strftime('%b %d')}", "bundle",
                             bundle["theme"], rows, notes=bundle.get("description", ""))
                st.toast("Saved to Projects", icon="💾")
        with c2:
            export_buttons({"slug": "bundle", "rows": rows}, key_prefix="bb")
        with st.expander("Bundle items — full table"):
            full_table(rows)
