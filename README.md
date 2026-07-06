# ⚡ PDF Hero

Find PDF products people are actually searching for, rate the profitable ones,
and let the AI build your product lines and bundle businesses — all from real,
live search data. Private multi-user workspaces with device-locked recovery.

## Pages (exactly these — nothing duplicated)
| Page | What it does |
|---|---|
| 🏠 **Home** | Workspace dashboard + quick actions |
| 📈 **Trend Discovery** | Today's hot searches, live-ranked moving niches, trending PDF opportunities |
| 🎯 **Niche Research** | One tap ranks every niche by live demand; deep-dive any of them (one niche per run — no category mixing) |
| 🔑 **Keyword Research** | Fully automatic — press Run with nothing typed and it finds keywords from the strongest live niches, grouped by niche |
| 🔗 **URL Research** | Analyze any public page — or run it empty and it pulls today's highest-pull **SEO Winners** instead of going stale |
| 🧠 **AI Studio** | Listing generator + product-line builder + **Bundle Business** builder (merged; template engine works with no AI key) |
| 📊 **Analytics** | Score distribution, niche depth, trend & intent mix, platform pull, duplicates, source health |
| 🗂️ **Projects** | Structured library grouped by type — delete one, selected, or ALL |
| ⚙️ **Settings** | Country default, providers, cache, change PIN, device recovery status, clear all data |

## Accounts
- Workspace names are **unique** — creating and signing in are separate, strict flows.
- **Recovery is device-locked**: the browser that creates a workspace becomes its
  only recovery key (stored privately in that browser). Forgot the PIN? The
  Forgot tab shows your workspace name(s) and lets you set a new PIN — on that
  device only. No other device can ever recover or reset it.

## Data honesty & speed
- Keywords come from live public autocomplete (Google, Bing, DuckDuckGo, YouTube,
  Amazon, Etsy, eBay, Walmart). Volumes are real when a provider key is set,
  otherwise clearly labeled estimates.
- Progress bars advance only when a fetch actually completes; cached and saved
  results render instantly with zero fake loading.
- 12 parallel workers with polite per-domain rate limits.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Deploy on Streamlit Cloud with `app.py` as the main file (Streamlit ≥ 1.39).
