"""PDF Hero — URL Research. Paste any public page to extract the phrases it's
built around — or press Run with nothing entered and it pulls today's
highest-SEO PDF phrases instead. It never just sits there asking for a link."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import (hero, inject_css, country_picker, detail_expanders,
                      export_buttons, full_table, geo_badge, keyword_cloud,
                      progress_runner)
from core import volume
from core.duplicate_checker import dedupe_rows
from core.opportunity_engine import enrich_rows
from core.pipeline import research_pipeline
from core.projects import save_project

inject_css()
user = st.session_state["user"]

hero("URL Research",
     "Drop in any public page to see the search phrases it's winning with — "
     "or run it empty and PDF Hero pulls the highest-pull SEO phrases growing "
     "across the web right now.")

country = country_picker("🌍 Country", key="url_country")
url = st.text_input("Public page URL (optional)",
                    placeholder="https://example.com/page — or leave empty for SEO Winners",
                    key="url_in")
run = st.button("🔗 Run URL Research", type="primary", key="url_run",
                use_container_width=True)

# phrases with proven marketplace pull — probes only, results are live
SEO_WINNER_PROBES = [
    "printable planner", "editable template", "printable calendar 2026",
    "budget spreadsheet printable", "worksheet pdf", "checklist template",
    "tracker printable", "invitation template", "digital download planner",
    "printable wall art", "resume template", "meal planner printable",
]

if run:
    if url.strip():
        from scrapers.website_scraper import scrape, combined_text
        from nlp.keyword_extractor import extract_keywords
        with st.spinner("Fetching and parsing the page…"):
            page = scrape(url.strip())
        if page.get("error"):
            st.error(page["error"])
        else:
            text = combined_text(page)
            kws = extract_keywords(text, top_n=30)
            rows = [{"keyword": k, "frequency": max(1, int(w * 10)),
                     "source_count": 1, "sources": ["page"], "best_rank": 1}
                    for k, w in kws]
            rows = dedupe_rows(rows)
            rows = volume.get_volumes(rows)
            rows = enrich_rows(rows)
            for i, r in enumerate(rows, 1):
                r["rank"] = i
            if rows:
                save_project(user["id"], f"URL · {page.get('title') or url.strip()[:40]}",
                             "url", url.strip(), rows)
            st.session_state["url_result"] = {"mode": "page", "page": page,
                                              "rows": rows, "country": country}
    else:
        st.info("No link given — pulling today's **SEO Winners** instead: the "
                "phrases with the widest live search pull.", icon="⚡")
        bar, update = progress_runner(1, "Scanning the strongest live SEO phrases")
        rows, _, cname = research_pipeline(
            SEO_WINNER_PROBES, country, include_shopping=True, keep=60,
            trends_top=6, progress=update)
        # widest live pull first — breadth of sources is the SEO signal
        rows.sort(key=lambda r: (-r.get("source_count", 0),
                                 -int(r.get("opportunity", 0))))
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        if rows:
            save_project(user["id"], f"SEO Winners ({cname})", "url",
                         "seo-winners", rows)
        st.session_state["url_result"] = {"mode": "winners", "rows": rows,
                                          "country": cname}

res = st.session_state.get("url_result")
if res and res.get("rows"):
    rows = res["rows"]
    if res["mode"] == "page":
        page = res["page"]
        st.markdown(f"### {page.get('title') or page.get('url','')}")
        if page.get("meta_description"):
            st.caption(page["meta_description"])
        st.markdown("##### PDF ideas drawn from this page — full detail")
    else:
        st.markdown(f"### ⚡ SEO Winners — {len(rows)} phrases with the widest live pull")
        geo_badge(res["country"])
        st.caption("Ranked by how many public search engines are actively suggesting "
                   "each phrase right now — the breadth that grows listings.")
    detail_expanders(rows, key_prefix="ur", limit=30)
    full_table(rows)
    keyword_cloud([(r["keyword"], r.get("opportunity", 1)) for r in rows[:40]])
    export_buttons({"slug": "url-research", "rows": rows,
                    "country": res.get("country", "")}, key_prefix="ur")
