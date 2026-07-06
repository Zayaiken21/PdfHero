"""CSV export."""
import io


def to_bytes(project: dict):
    from utils.tables import rows_to_df
    df = rows_to_df(project.get("rows", []))
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8"), "text/csv", f"{project.get('slug','project')}.csv"
