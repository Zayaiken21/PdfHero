"""PDF export via ReportLab platypus."""
import io


def to_bytes(project: dict):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.7 * inch,
                            bottomMargin=0.7 * inch)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1x", parent=styles["Title"], textColor=colors.HexColor("#2B2350"))
    h2 = ParagraphStyle("h2x", parent=styles["Heading2"], textColor=colors.HexColor("#5B44C9"))
    body = styles["BodyText"]
    story = [Paragraph(project.get("name", "PDF SEO Intel Report"), h1),
             Paragraph(f"Type: {project.get('type','')} · Seed: {project.get('seed','')} "
                       f"· Created: {project.get('created','')}", body),
             Spacer(1, 12)]
    rows = project.get("rows", [])
    if rows:
        story.append(Paragraph("Ranked PDF opportunities", h2))
        data = [["#", "Search phrase", "Score", "Searches/mo", "Trend", "Trending in"]]
        for r in rows[:25]:
            data.append([str(r.get("rank", "")), r.get("keyword", "")[:36],
                         str(r.get("opportunity", "")), r.get("volume_label", ""),
                         r.get("trend_label", ""), (r.get("top_region", "") or "")[:16]])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0EA5E9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFE8FB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFF9FE")]),
        ]))
        story += [table, Spacer(1, 14)]

        # Sell-ready detail for the top ideas
        story.append(Paragraph("Sell-ready titles & descriptions (top 10)", h2))
        for r in rows[:10]:
            titles = r.get("pdf_titles") or []
            if not titles:
                continue
            story.append(Paragraph(
                f"<b>{r.get('rank','')}. {r.get('keyword','')}</b> "
                f"— {r.get('opportunity','')}/100 · {r.get('product_type','PDF')}", body))
            for t in titles:
                story.append(Paragraph(f"&nbsp;&nbsp;• {t}", body))
            if r.get("pdf_description"):
                story.append(Paragraph(f"<i>{r['pdf_description']}</i>", body))
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 6))
    listing = (project.get("listing") or {}).get("primary") or {}
    if listing:
        story.append(Paragraph("AI listing", h2))
        for title in listing.get("seo_titles", [])[:5]:
            story.append(Paragraph(f"• {title}", body))
        story.append(Spacer(1, 8))
        story.append(Paragraph(listing.get("short_description", ""), body))
        story.append(Spacer(1, 8))
        for para in (listing.get("long_description", "") or "").split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), body))
        tags = ", ".join(listing.get("tags", [])[:60])
        if tags:
            story += [Spacer(1, 8), Paragraph("Tags", h2), Paragraph(tags, body)]
    doc.build(story)
    return buf.getvalue(), "application/pdf", f"{project.get('slug','project')}.pdf"
