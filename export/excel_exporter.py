"""Excel export — Keywords, Listing, and Tags sheets."""
import io


def to_bytes(project: dict):
    import pandas as pd
    from utils.tables import rows_to_df
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        rows_to_df(project.get("rows", [])).to_excel(writer, sheet_name="Keywords", index=False)
        listing = (project.get("listing") or {}).get("primary") or project.get("listing") or {}
        if listing:
            flat = []
            for key, value in listing.items():
                if isinstance(value, (str, int, float)):
                    flat.append({"field": key, "value": str(value)[:32000]})
                elif isinstance(value, list) and value and isinstance(value[0], str):
                    flat.append({"field": key, "value": " | ".join(value)[:32000]})
            if flat:
                pd.DataFrame(flat).to_excel(writer, sheet_name="Listing", index=False)
            mtags = listing.get("marketplace_tags") or {}
            if mtags:
                width = max(len(v) for v in mtags.values())
                table = {k: v + [""] * (width - len(v)) for k, v in mtags.items()}
                pd.DataFrame(table).to_excel(writer, sheet_name="Tags", index=False)
    return buf.getvalue(), \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", \
        f"{project.get('slug','project')}.xlsx"
