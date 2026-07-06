"""PDF Hero — entrypoint & router.

One place defines the whole app: brand, theme, the private-workspace gate,
the device recovery key, and exactly these pages —

  🏠 Home · 📈 Trend Discovery · 🎯 Niche Research · 🔑 Keyword Research
  🔗 URL Research · 🧠 AI Studio · 📊 Analytics · 🗂️ Projects · ⚙️ Settings

Everything the old Discover/Research/My Ideas/Auto Pilot/Marketplace/AI
Generator/Product Line pages did now lives inside these, with no duplicated
functions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

st.set_page_config(page_title="PDF Hero", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

from utils.ui import inject_css, require_user, sync_device_id  # noqa: E402

inject_css()
sync_device_id()

with st.sidebar:
    st.markdown(
        '<div style="font-family:Sora,sans-serif;font-weight:800;font-size:1.25rem;'
        'letter-spacing:-.01em;padding:.15rem 0 .35rem;">⚡ PDF <span '
        'style="color:#67E8F9;">Hero</span></div>',
        unsafe_allow_html=True)

user = require_user()          # stops here until signed in

pages = [
    st.Page("views/home.py",         title="Home",             icon="🏠", default=True),
    st.Page("views/trends.py",       title="Trend Discovery",  icon="📈"),
    st.Page("views/niche.py",        title="Niche Research",   icon="🎯"),
    st.Page("views/keywords.py",     title="Keyword Research", icon="🔑"),
    st.Page("views/url_research.py", title="URL Research",     icon="🔗"),
    st.Page("views/studio.py",       title="AI Studio",        icon="🧠"),
    st.Page("views/analytics.py",    title="Analytics",        icon="📊"),
    st.Page("views/projects.py",     title="Projects",         icon="🗂️"),
    st.Page("views/settings.py",     title="Settings",         icon="⚙️"),
]

st.navigation(pages, position="sidebar").run()
