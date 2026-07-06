"""DataFrame helpers usable outside Streamlit (exports, tests)."""


def rows_to_df(rows):
    import pandas as pd
    cols = ["rank", "keyword", "pdf_title", "pdf_description", "product_type",
            "opportunity", "volume_label", "trending_in", "niche", "intent",
            "trend_label", "category", "platforms", "source_count"]
    data = []
    for r in rows or []:
        data.append({
            "rank": r.get("rank", ""),
            "keyword": r.get("keyword"),
            "pdf_title": (r.get("pdf_titles") or [""])[0],
            "pdf_description": r.get("pdf_description", ""),
            "product_type": r.get("product_type", ""),
            "trending_in": r.get("top_region", ""),
            "opportunity": r.get("opportunity"),
            "volume_label": r.get("volume_label", ""),
            "niche": r.get("niche", r.get("category", "")),
            "intent": r.get("intent"),
            "trend_label": r.get("trend_label", ""),
            "category": r.get("category"),
            "platforms": ", ".join(r.get("platforms", [])),
            "source_count": r.get("source_count", 0),
        })
    return pd.DataFrame(data, columns=cols)
