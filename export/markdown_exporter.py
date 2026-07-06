"""Markdown export — human-readable, sell-ready PDF idea report."""


def to_bytes(project: dict):
    lines = [f"# {project.get('name','PDF Ideas')}",
             f"*Type:* {project.get('type','')} · *Topic:* {project.get('seed','')} · "
             f"*Country:* {project.get('country','—')} · *Created:* {project.get('created','')}",
             ""]
    rows = project.get("rows", [])
    if rows:
        lines += ["## Ready-to-sell PDF ideas", ""]
        for r in rows[:40]:
            titles = r.get("pdf_titles") or []
            lines.append(f"### {r.get('rank','')}. {r.get('keyword','')}  "
                         f"— {r.get('opportunity','')}/100")
            lines.append(f"*{r.get('volume_label','')} · {r.get('trend_label','')} · "
                         f"trending in {r.get('top_region','—')} · "
                         f"{r.get('intent','')} intent · niche: "
                         f"{r.get('niche', r.get('category',''))}*")
            lines.append("")
            if titles:
                lines.append(f"**Sell it as ({r.get('product_type','PDF')}):**")
                for t in titles:
                    lines.append(f"- {t}")
            if r.get("pdf_description"):
                lines += ["", f"**What it could be:** {r['pdf_description']}"]
            inside = r.get("whats_inside") or []
            if inside:
                lines.append(f"**Pages/sections:** {', '.join(inside)}")
            if r.get("platforms"):
                lines.append(f"**Best platforms:** {', '.join(r['platforms'])}")
            lines.append("")

    listing = (project.get("listing") or {}).get("primary") or {}
    if listing:
        lines += ["---", "## AI marketplace listing", ""]
        for title in listing.get("seo_titles", [])[:5]:
            lines.append(f"- **{title}**")
        lines += ["", f"**Short description:** {listing.get('short_description','')}", "",
                  listing.get("long_description", ""), "", "### Tags",
                  ", ".join(listing.get("tags", [])), ""]
        for platform, desc in (listing.get("platform_descriptions") or {}).items():
            lines += [f"### {platform.title()} description", desc, ""]

    if project.get("notes"):
        lines += ["---", f"_{project['notes']}_"]
    text = "\n".join(lines)
    return text.encode("utf-8"), "text/markdown", f"{project.get('slug','project')}.md"
