"""PDF Hero — shared Streamlit UI helpers.

Page chrome, hero, badges, chips, keyword cloud, full-detail expanders,
exports, the device-key sync, and the strict workspace gate
(sign in / create / device-locked recovery).
"""
import hashlib
import html
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

APP_NAME = "PDF Hero"
KICKER = "PDF HERO · SEO INTELLIGENCE"


# ── page chrome ──────────────────────────────────────────────────────
def inject_css():
    """Load the theme once per run. st.set_page_config lives in app.py only."""
    css = ROOT / "styles" / "main.css"
    if css.exists():
        st.markdown(f"<style>{css.read_text()}</style>", unsafe_allow_html=True)
    st.session_state.setdefault("picked_keywords", [])


def setup_page(title: str = "", icon: str = "⚡", layout: str = "wide"):
    """Kept for compatibility — under the app.py router this only ensures CSS
    and session defaults exist (set_page_config is already done centrally)."""
    inject_css()


def hero(title: str, subtitle: str, kicker: str = KICKER):
    st.markdown(
        f"""<div class="si-hero"><div class="si-kicker">{html.escape(kicker)}</div>
        <h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>""",
        unsafe_allow_html=True,
    )


# ── badges & chips ───────────────────────────────────────────────────
def score_class(score: int) -> str:
    if score >= 85:
        return "hot"
    if score >= 70:
        return "strong"
    if score >= 55:
        return "viable"
    return "weak"


def score_badge(score: int) -> str:
    return f'<span class="si-score {score_class(score)}">{int(score)}</span>'


def chips(items, kind: str = "") -> str:
    cls = f"si-chip {kind}".strip()
    return " ".join(f'<span class="{cls}">{html.escape(str(i))}</span>' for i in items or [])


def trend_chip(label: str) -> str:
    kind = "rise" if "Ris" in (label or "") else ""
    return f'<span class="si-chip {kind}">{html.escape(label or "")}</span>'


def geo_badge(country: str):
    st.markdown(f'<span class="si-chip geo">{html.escape(country or "")}</span>',
                unsafe_allow_html=True)


# ── keyword cloud (contained: capped sizes, wraps cleanly on phones) ─
def keyword_cloud(pairs, max_items: int = 40):
    """pairs: [(keyword, weight)] — compact tag cloud that never overflows."""
    pairs = sorted(pairs or [], key=lambda p: -p[1])[:max_items]
    if not pairs:
        st.caption("No keywords yet.")
        return
    weights = [p[1] for p in pairs]
    lo, hi = min(weights), max(weights)
    palette = ["#B4A6FF", "#8FE3C0", "#FFC98A", "#9AB6FF", "#E6EAF2"]
    spans = []
    for i, (kw, w) in enumerate(pairs):
        rel = 0.0 if hi == lo else (w - lo) / (hi - lo)
        size = 0.74 + rel * 0.34          # 0.74rem – 1.08rem: readable, never huge
        color = palette[i % len(palette)]
        spans.append(f'<span style="font-size:{size:.2f}rem;color:{color};">'
                     f'{html.escape(str(kw))}</span>')
    st.markdown(f'<div class="si-cloud">{" ".join(spans)}</div>', unsafe_allow_html=True)


from utils.tables import rows_to_df  # noqa: E402  (re-export)


# ── exports ──────────────────────────────────────────────────────────
def export_buttons(project: dict, key_prefix: str = "exp"):
    """CSV / Excel / JSON / PDF / Markdown downloads for a project dict."""
    from export import csv_exporter, excel_exporter, json_exporter, markdown_exporter, pdf_exporter
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        data, mime, name = csv_exporter.to_bytes(project)
        st.download_button("CSV", data, name, mime, key=f"{key_prefix}_csv",
                           use_container_width=True)
    with c2:
        data, mime, name = excel_exporter.to_bytes(project)
        st.download_button("Excel", data, name, mime, key=f"{key_prefix}_xlsx",
                           use_container_width=True)
    with c3:
        data, mime, name = json_exporter.to_bytes(project)
        st.download_button("JSON", data, name, mime, key=f"{key_prefix}_json",
                           use_container_width=True)
    with c4:
        try:
            data, mime, name = pdf_exporter.to_bytes(project)
            st.download_button("PDF", data, name, mime, key=f"{key_prefix}_pdf",
                               use_container_width=True)
        except Exception as exc:
            st.caption(f"PDF export unavailable: {exc}")
    with c5:
        data, mime, name = markdown_exporter.to_bytes(project)
        st.download_button("Markdown", data, name, mime, key=f"{key_prefix}_md",
                           use_container_width=True)


# ── real progress (advances only when work completes) ────────────────
def progress_runner(total: int, label: str = "Fetching"):
    bar = st.progress(0.0, text=f"{label}…")

    def update(done, total_inner, detail=""):
        frac = min(1.0, done / max(1, total_inner))
        bar.progress(frac, text=f"{label} · {done}/{total_inner} · {str(detail)[:56]}")

    return bar, update


# ── device key (recovery is locked to this device) ───────────────────
def sync_device_id():
    """One-time per browser: a private device key is created in this browser's
    local storage and mirrored into the URL so the app can read it. It never
    leaves the app and only unlocks recovery for workspaces created here."""
    if st.session_state.get("device_id"):
        return
    dev = st.query_params.get("device")
    if dev:
        st.session_state["device_id"] = str(dev)
        return
    try:
        import streamlit.components.v1 as components
        components.html(
            """<script>
            try {
              const KEY = 'pdfhero_device_id';
              let id = localStorage.getItem(KEY);
              if (!id) {
                id = (window.crypto && crypto.randomUUID)
                     ? crypto.randomUUID()
                     : 'd-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
                localStorage.setItem(KEY, id);
              }
              const url = new URL(window.parent.location.href);
              if (url.searchParams.get('device') !== id) {
                url.searchParams.set('device', id);
                window.parent.location.replace(url.toString());
              }
            } catch (e) { /* private mode / blocked storage: recovery simply unavailable */ }
            </script>""",
            height=0,
        )
    except Exception:
        pass


# ── workspace gate: sign in · create · device-locked recovery ────────
def require_user():
    """Gate the whole app. Returns the signed-in user dict, or renders the
    sign-in screen and stops."""
    user = st.session_state.get("user")
    if user:
        with st.sidebar:
            st.markdown(f'<div class="ph-workspace">⚡ <b>{html.escape(user["username"])}</b></div>',
                        unsafe_allow_html=True)
            if st.button("Sign out", key="signout_btn", use_container_width=True):
                st.session_state.pop("user", None)
                st.rerun()
        return user

    from core import db

    hero(APP_NAME,
         "Find PDF products people are actually searching for, rate the profitable "
         "ones, and build sellable bundles — real search data, private workspaces.")

    device_id = st.session_state.get("device_id", "")

    t_in, t_new, t_forgot = st.tabs(["🔓 Sign in", "✨ Create workspace", "🛟 Forgot PIN?"])

    with t_in:
        with st.form("ph_signin"):
            u = st.text_input("Workspace name", placeholder="your unique name", key="in_user")
            p = st.text_input("PIN", type="password", key="in_pin")
            go = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if go:
            found, msg = db.login_user(u, p, device_id=device_id)
            if found:
                st.session_state["user"] = found
                st.toast(msg, icon="⚡")
                st.rerun()
            else:
                st.error(msg)

    with t_new:
        st.caption("Names are unique across the app. Your projects are private to "
                   "your workspace, and this device becomes the only recovery key.")
        with st.form("ph_create"):
            u = st.text_input("Pick a unique name", placeholder="2–24 chars · letters, numbers, _ .",
                              key="new_user")
            c1, c2 = st.columns(2)
            p1 = c1.text_input("Create a PIN (4+ chars)", type="password", key="new_pin1")
            p2 = c2.text_input("Repeat PIN", type="password", key="new_pin2")
            go = st.form_submit_button("Create my workspace", type="primary",
                                       use_container_width=True)
        if go:
            if (p1 or "") != (p2 or ""):
                st.error("PINs don't match.")
            else:
                made, msg = db.register_user(u, p1, device_id=device_id)
                if made:
                    st.session_state["user"] = made
                    st.toast(msg, icon="✨")
                    st.rerun()
                else:
                    st.error(msg)

    with t_forgot:
        st.caption("Strict by design: recovery only works on the device a workspace "
                   "was created on. Other devices can never see or reset it.")
        if not device_id:
            st.warning("This browser has no device key yet (storage may be blocked or "
                       "still loading). Reload once, or use the device you signed up on.")
        else:
            mine = db.recover_usernames_by_device(device_id)
            if not mine:
                st.info("No workspaces are registered to this device.")
            else:
                st.success(f"This device owns: **{', '.join(mine)}**")
                with st.form("ph_recover"):
                    pick = st.selectbox("Workspace", mine, key="rec_user")
                    c1, c2 = st.columns(2)
                    np1 = c1.text_input("New PIN (4+ chars)", type="password", key="rec_pin1")
                    np2 = c2.text_input("Repeat new PIN", type="password", key="rec_pin2")
                    go = st.form_submit_button("Reset PIN on this device", type="primary",
                                               use_container_width=True)
                if go:
                    if (np1 or "") != (np2 or ""):
                        st.error("PINs don't match.")
                    else:
                        ok, msg = db.reset_pin_with_device(pick, device_id, np1)
                        (st.success if ok else st.error)(msg)
    st.stop()


# ── full-detail collapsible results ──────────────────────────────────
def detail_expanders(rows, key_prefix: str = "dt", limit: int = 30):
    """Collapsible FULL-detail card per idea — rank, exact search phrase,
    sellable titles, demand, trend, niche, platforms, score breakdown, and why."""
    for row in (rows or [])[:limit]:
        rank = row.get("rank", "")
        score = int(row.get("opportunity", 0))
        header = (f"#{rank} · {row.get('keyword','')} — {score}/100 · "
                  f"{row.get('volume_label','')} · {row.get('trend_label','')}")
        with st.expander(header, expanded=False):
            top = st.columns([1, 1, 1, 1, 1])
            top[0].metric("Opportunity", f"{score}/100")
            top[1].metric("Searches/mo", row.get("volume_label", "—"))
            top[2].metric("Trend", row.get("trend_label", "—"))
            top[3].metric("Trending in", row.get("top_region", "—"))
            top[4].metric("Competition", row.get("competition_label", "—"))

            st.markdown('<div class="si-detail"><b>What people actually type into '
                        'search:</b> '
                        f'“{html.escape(row.get("keyword",""))}”</div>',
                        unsafe_allow_html=True)

            titles = row.get("pdf_titles") or []
            if titles:
                st.markdown(f"**Sell it as a {row.get('product_type','PDF')} — "
                            "ready-to-use title options:**")
                for t in titles:
                    st.markdown(f'<div class="si-title-idea">{html.escape(t)}</div>',
                                unsafe_allow_html=True)
            if row.get("pdf_description"):
                st.markdown(f'<div class="si-desc">{html.escape(row["pdf_description"])}</div>',
                            unsafe_allow_html=True)
            inside = row.get("whats_inside") or []
            if inside:
                st.markdown("**Pages / sections to include:** " + ", ".join(inside))

            meta_line = (f"**Niche:** {row.get('niche', row.get('category','General'))} · "
                         f"**Category:** {row.get('category','General')} · "
                         f"**Intent:** {row.get('intent','—')} "
                         f"(buyer signal {round(float(row.get('buyer_intent',0))*100)}%) · "
                         f"**Seasonality:** {row.get('seasonality','—')} · "
                         f"**Found on {row.get('source_count',0)} source(s):** "
                         + ", ".join(row.get("sources", [])))
            st.markdown(meta_line)
            if row.get("platforms"):
                st.markdown("**Best platforms:** " + chips(row["platforms"], "accent"),
                            unsafe_allow_html=True)
            if row.get("why"):
                st.markdown(f'<div class="si-detail">{html.escape(row["why"])}</div>',
                            unsafe_allow_html=True)
            br = row.get("breakdown") or {}
            if br:
                st.caption("Score breakdown (each signal /10)")
                cols = st.columns(4)
                for i, (name, val) in enumerate(br.items()):
                    cols[i % 4].caption(f"{name.replace('_',' ').title()}: **{val}**")


def full_table(rows):
    """Full-width dataframe with pinned column widths so text never bleeds."""
    df = rows_to_df(rows)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        height=min(640, 60 + 35 * max(1, len(df))),
        column_config={
            "rank": st.column_config.NumberColumn("#", width="small"),
            "keyword": st.column_config.TextColumn("What people search", width="medium"),
            "pdf_title": st.column_config.TextColumn("Sell it as (PDF title)", width="large"),
            "pdf_description": st.column_config.TextColumn("What it could be", width="large"),
            "product_type": st.column_config.TextColumn("Type", width="small"),
            "opportunity": st.column_config.ProgressColumn("Score", min_value=0,
                                                           max_value=100, format="%d",
                                                           width="small"),
            "volume_label": st.column_config.TextColumn("Searches/mo", width="small"),
            "trending_in": st.column_config.TextColumn("Trending in", width="small"),
            "niche": st.column_config.TextColumn("Niche", width="small"),
            "intent": st.column_config.TextColumn("Intent", width="small"),
            "trend_label": st.column_config.TextColumn("Trend", width="small"),
            "category": st.column_config.TextColumn("Category", width="small"),
            "platforms": st.column_config.TextColumn("Best platforms", width="medium"),
            "source_count": st.column_config.NumberColumn("Sources", width="small"),
        })


# ── country picker (FIX: unique key per placement — no duplicate IDs) ─
def country_picker(label: str = "Country to search", key: str = ""):
    """Selectbox synced with session_state['country'].

    Every placement passes (or derives) a UNIQUE key, which is what caused the
    StreamlitDuplicateElementId crash before: the same label rendered in two
    tabs produced identical element IDs. Never write to st.session_state[key]
    here — Streamlit owns widget keys after instantiation.
    """
    from core import geo as geo_mod
    names = geo_mod.names()
    current = st.session_state.get("country", geo_mod.DEFAULT)
    idx = names.index(current) if current in names else names.index(geo_mod.DEFAULT)
    widget_key = key or ("country_" + hashlib.sha1(label.encode()).hexdigest()[:8])
    choice = st.selectbox(label, names, index=idx, key=widget_key,
                          help="Autocomplete, Trends, and volume are pulled for this "
                               "country.")
    st.session_state["country"] = choice
    return choice
