"""PDF Hero — Settings. Country default, AI + volume providers, source
health, cache, account security (PIN + device recovery), and the switches
that clear your data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from utils.ui import hero, inject_css, country_picker
from utils.cache import cache
from utils.http import SOURCE_HEALTH
from core import config, db
from core.projects import delete_all_projects, list_projects
from core.volume import status as vol_status
from ai import provider as ai_provider

inject_css()
user = st.session_state["user"]

hero("Settings",
     "Your defaults, your providers, your data. Recovery stays locked to the "
     "device that created this workspace.")

st.markdown("#### 🌍 Default country")
country_picker("Country used for new searches", key="settings_country")
st.caption("Every research page starts here; you can still switch per search.")

st.markdown("#### 🤖 AI provider")
stat = ai_provider.status()
c1, c2 = st.columns([1, 2])
c1.metric("Provider", stat["provider"])
c2.metric("Status", "Ready ✓" if stat["ok"] else "Unavailable ✗")
st.caption(stat["detail"])
if st.button("Run live AI test", key="ai_test"):
    ok, msg = ai_provider.test_call()
    (st.success if ok else st.error)(f"Test reply: {msg}")
st.caption("Set `AI_PROVIDER` in Streamlit secrets to `ollama`, `openai`, "
           "`anthropic`, or `gemini`. AI Studio works without one via the "
           "template engine — a provider upgrades the copy.")

st.markdown("#### 📊 Search-volume source")
vol = vol_status()
st.metric("Volume", "Real data ✓" if vol["real_data"] else "Smart estimate")
st.caption(vol["label"] + " — add `KEYWORDS_EVERYWHERE_API_KEY` or "
           "`DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD` for exact monthly volume.")

st.markdown("#### 📡 Data-source health (this session)")
if SOURCE_HEALTH:
    try:
        import pandas as pd
        rows = [{"source": name, "ok": h.get("ok", 0), "failed": h.get("fail", 0),
                 "last error": (h.get("last_error") or "")[:60]}
                for name, h in sorted(SOURCE_HEALTH.items())]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    except Exception:
        st.json(SOURCE_HEALTH)
    st.caption("Some marketplace endpoints are bot-guarded and can fail on certain "
               "networks — the app keeps every other source and carries on.")
else:
    st.caption("No requests made yet this session.")

st.markdown("#### 🔐 Account & security")
device_id = st.session_state.get("device_id", "")
bound = db.device_binding(user["id"])
if bound and device_id and bound == device_id:
    st.success("This is your workspace's recovery device ✓ — forgotten PINs can "
               "only be reset here.")
elif bound:
    st.warning("Your recovery device is a different one. PIN recovery only works "
               "there — by design, no other device can unlock this workspace.")
else:
    st.info("No recovery device bound yet — it binds automatically the next time "
            "you sign in from your main device.")

with st.expander("Change my PIN"):
    with st.form("set_change_pin"):
        old = st.text_input("Current PIN", type="password", key="cp_old")
        c1, c2 = st.columns(2)
        n1 = c1.text_input("New PIN (4+ chars)", type="password", key="cp_n1")
        n2 = c2.text_input("Repeat new PIN", type="password", key="cp_n2")
        go = st.form_submit_button("Update PIN", type="primary",
                                   use_container_width=True)
    if go:
        if (n1 or "") != (n2 or ""):
            st.error("New PINs don't match.")
        else:
            ok, msg = db.change_pin(user["id"], old, n1)
            (st.success if ok else st.error)(msg)

st.markdown("#### 🧹 Cache & data")
stats = cache.stats()
c1, c2, c3 = st.columns(3)
c1.metric("Cache entries", stats.get("entries", 0))
c2.metric("Cache size", f"{stats.get('megabytes', 0)} MB")
c3.metric("TTL", f"{config.get('CACHE_TTL_HOURS')}h")
if st.button("Clear fetch cache", key="set_cache_clear"):
    cache.clear()
    st.success("Cache cleared — the next scans pull completely fresh data.")

with st.expander("🧨 Clear ALL my data"):
    st.caption("Deletes every project in this workspace. The workspace itself and "
               "your sign-in stay. This cannot be undone.")
    n_projects = len(list_projects(user["id"]))
    st.write(f"Projects that will be deleted: **{n_projects}**")
    typed = st.text_input(f"Type your workspace name (`{user['username']}`) to confirm",
                          key="set_wipe_typed")
    if st.button("Delete everything in my workspace", key="set_wipe",
                 disabled=typed.strip().lower() != user["username"]):
        n = delete_all_projects(user["id"])
        cache.clear()
        st.success(f"Deleted {n} project(s) and cleared the cache. Fresh start.")
        st.rerun()
