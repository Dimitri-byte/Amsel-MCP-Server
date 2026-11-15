"""Turn Tome/Lore content into Markdown for the model to read."""

from __future__ import annotations

from collections import defaultdict

from .model import Context, Lore, Tome, find_one, short_type, subpage_html
from .text import html_to_text, normalize


def _id(item: dict) -> str:
    return item["idHash"][:8]


def _states(tome: Tome, page: dict) -> str:
    states = [f"{tome.sessions.get(s.get('relatedSessionId'), 'session ?')}: {s.get('state')}" for s in page.get("pageStates") or []]
    return "; ".join(states)


def _backlink_lines(ctx: Context, backlinks: dict[str, list[str]], page_id: str) -> list[str]:
    refs = backlinks.get(page_id) or []
    if not refs:
        return []
    return ["", "## Referenced by", *[f"- [[{ctx.name_of_id(r)}]]" for r in refs]]


# --- Tome ------------------------------------------------------------------

def tome_outline(tome: Tome, with_summaries: bool = False) -> str:
    ctx = Context(tome=tome)
    lines = [f"# {tome.name} — story outline", ""]

    def walk(page: dict, depth: int) -> None:
        extra = []
        if page.get("ribbon"):
            extra.append(f"ribbon {page['ribbon']}")
        st = _states(tome, page)
        if st:
            extra.append(st)
        suffix = f" — {', '.join(extra)}" if extra else ""
        lines.append(f"{'  ' * depth}- [{short_type(page['type'])}] {page['pageName']} ({_id(page)}){suffix}")
        if with_summaries and page.get("summary"):
            s = html_to_text(page["summary"], ctx.label).replace("\n", " ")
            if s:
                lines.append(f"{'  ' * (depth + 1)}  {s[:300]}{'…' if len(s) > 300 else ''}")
        for child in tome.children(page):
            walk(child, depth + 1)

    for root in tome.roots():
        walk(root, 0)
    return "\n".join(lines)


def tome_data_pages(tome: Tome, page_type: str | None = None) -> str:
    groups: dict[str, list[dict]] = defaultdict(list)
    for pid in tome.data_page_order:
        p = tome.data_pages[pid]
        if page_type and normalize(page_type) not in normalize(p["type"]):
            continue
        groups[short_type(p["type"])].append(p)
    if not groups:
        return f"No data pages{f' of type {page_type!r}' if page_type else ''}."
    lines = [f"# {tome.name} — data pages", ""]
    for t, pages in groups.items():
        lines.append(f"## {t} ({len(pages)})")
        for p in pages:
            star = " ★" if p.get("isFavorite") else ""
            player = " (player)" if p.get("isPlayer") else ""
            lines.append(f"- {p['pageName']} ({_id(p)}){player}{star}")
        lines.append("")
    return "\n".join(lines).rstrip()


def tome_page(tome: Tome, lore: Lore | None, ref: str) -> str:
    page = find_one(tome.all_pages, ref, lambda p: p["pageName"], "Tome page")
    ctx = Context(tome=tome, lore=lore)
    lines = [f"# {page['pageName']}", ""]
    meta = [f"type: {short_type(page['type'])}", f"id: {page['idHash']}"]
    if page["idHash"] in tome.story_pages:
        parent = tome.story_pages.get(page.get("parentId") or "")
        if parent:
            meta.append(f"parent: [[{parent['pageName']}]]")
        if page.get("ribbon"):
            meta.append(f"ribbon: {page['ribbon']}")
        st = _states(tome, page)
        if st:
            meta.append(f"states: {st}")
    if page.get("aliases"):
        meta.append("aliases: " + ", ".join(map(str, page["aliases"])))
    lines += [" · ".join(meta), ""]
    cover = (page.get("coverImage") or {}).get("relatedImage")
    if cover:
        img = next((i for i in tome.data.get("importedImages", []) if i.get("idHash") == cover), {})
        lines += [f"[cover image: {img.get('displayedName', '?')}]", ""]

    summary = html_to_text(page.get("summary"), ctx.label)
    if summary:
        lines += ["## Summary", summary, ""]

    content = html_to_text(page.get("content"), ctx.label)
    if content:
        lines += ["## Content", content, ""]

    for sp in page.get("subPages") or []:
        title = sp.get("title") or short_type(sp.get("type", ""))
        if sp.get("type") == "checker":
            mods = ((sp.get("contentByType") or {}).get("checker") or {}).get("modules", [])
            body = "\n\n".join(
                f"### {m.get('title') or '—'}\n{html_to_text(m.get('content'), ctx.label)}"
                for m in mods if html_to_text(m.get("content"))
            )
            if body:
                lines += [f"## {title}", body, ""]
        else:
            text = "\n\n".join(html_to_text(h, ctx.label) for h in subpage_html(sp)).strip()
            if text:
                lines += [f"## {title}", text, ""]

    if page["idHash"] in tome.story_pages:
        kids = tome.children(page)
        if kids:
            lines += ["## Children", *[f"- [{short_type(k['type'])}] {k['pageName']}" for k in kids], ""]

    rels = [ctx.label(r.get("pageType", ""), r["idHash"]) or ctx.name_of_id(r["idHash"]) for r in page.get("relations") or []]
    if rels:
        lines += ["## Relations", *[f"- [[{r}]]" for r in rels], ""]

    lines += _backlink_lines(ctx, tome.backlinks, page["idHash"])
    return "\n".join(lines).rstrip()


def tome_arcanes(tome: Tome, lore: Lore | None, arcane_type: str | None = None) -> str:
    ctx = Context(tome=tome, lore=lore)
    items = [a for a in tome.arcanes.values() if not arcane_type or normalize(a["type"]) == normalize(arcane_type)]
    if not items:
        return "No arcanes."
    lines = [f"# {tome.name} — arcanes ({len(items)})", ""]
    for a in items:
        text = html_to_text(a.get("text"), ctx.label).replace("\n", " ")
        lines.append(f"- **{a['type']}** ({_id(a)}): {text}")
        for r in a.get("results") or []:
            sess = tome.sessions.get(r.get("relatedSessionIdHash"), "session ?")
            bits = []
            if "state" in r:
                bits.append("result: not decided yet" if r["state"] == "tbd" else f"result: {r['state']}")
            if "mood" in r:
                bits.append("mood: not set" if not r["mood"] else f"mood: {r['mood']}/5")
            if "characters" in r:
                names = [ctx.name_of_id(c.get("idHash", "")) for c in r["characters"]]
                bits.append("characters: " + (", ".join(f"[[{n}]]" for n in names) if names else "none yet"))
            if "choices" in r:
                bits.append("options: " + " / ".join(
                    (f"**{c.get('content', '')}** (chosen)" if c.get("isSelected") else c.get("content", "")) for c in r["choices"]))
            if "number" in r:
                bits.append(f"count: {r['number']}")
            com = html_to_text(r.get("commentary"), ctx.label).replace("\n", " ")
            if com:
                bits.append(f"note: {com}")
            if bits:
                lines.append(f"  - {sess} — {'; '.join(bits)}")
        where = tome.backlinks.get(a["idHash"]) or []
        where = [x for x in where if x != a["idHash"]]
        if where:
            lines.append("  - appears in: " + ", ".join(f"[[{ctx.name_of_id(w)}]]" for w in where))
    return "\n".join(lines)


def tome_notes(tome: Tome) -> str:
    notes = tome.data.get("notes") or []
    if not notes:
        return "No session notes."
    lines = [f"# {tome.name} — session notes", ""]
    for n in notes:
        sess = tome.sessions.get(n.get("relatedSessionId"), "session ?")
        lines += [f"## {sess} — {n.get('dateSys', '')}", html_to_text(n.get("content")) or str(n.get("content", "")), ""]
    return "\n".join(lines).rstrip()


# --- Lore ------------------------------------------------------------------

def lore_pages(lore: Lore, template: str | None = None) -> str:
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in lore.pages.values():
        t = lore.template_of(p)
        tname = t["name"] if t else "(no template)"
        if template and normalize(template) not in normalize(tname):
            continue
        groups[tname].append(p)
    if not groups:
        return f"No Lore pages{f' for template {template!r}' if template else ''}."
    lines = [f"# {lore.name} — pages", ""]
    for tname in sorted(groups, key=normalize):
        pages = sorted(groups[tname], key=lambda p: normalize(p["name"]))
        lines.append(f"## {tname} ({len(pages)})")
        lines += [f"- {p['name']} ({_id(p)}){' ★' if p.get('isFavorite') else ''}" for p in pages]
        lines.append("")
    return "\n".join(lines).rstrip()


def lore_templates(lore: Lore) -> str:
    counts: dict[str, int] = defaultdict(int)
    for p in lore.pages.values():
        counts[p.get("templateId")] += 1
    kit = lore.kind == "lorekit"
    title = "template kit (import it in the Lore app to use these templates)" if kit else "templates"
    lines = [f"# {lore.name} — {title}", ""]
    for t in sorted(lore.templates.values(), key=lambda t: (normalize(lore.category_name(t)), normalize(t["name"]))):
        mods = ", ".join(f"{m.get('header') or '—'} ({short_type(m.get('typeCodeModule', ''))})" for m in _ordered_modules(t))
        count = "" if kit else f" — {counts[t['idHash']]} pages"
        lines.append(f"- **{t['name']}** [{lore.category_name(t)}]{count} — modules: {mods}")
    return "\n".join(lines)


def lore_template(lore: Lore, ref: str) -> str:
    """One template in detail: its modules in layout order, rune fields and mirror targets."""
    t = find_one(lore.templates, ref, lambda t: t["name"], "template")
    used = sum(1 for p in lore.pages.values() if p.get("templateId") == t["idHash"])
    lines = [f"# {t['name']}", "", f"category: {lore.category_name(t)} · id: {t['idHash']}"
             + ("" if lore.kind == "lorekit" else f" · {used} pages"), ""]
    for m in _ordered_modules(t):
        mtype = m.get("typeCodeModule", "")
        hidden = " (hidden)" if m.get("isHidden") else ""
        lines.append(f"## {m.get('header') or '—'} — {short_type(mtype)}{hidden}")
        if mtype == "LM_Rune":
            rt = lore.rune_templates.get(m.get("linkedModuleTemplateId"))
            if rt:
                lines.append(f"rune: {rt['name']}")
                lines += [f"- {r.get('label') or '?'} ({short_type(r.get('type', ''))})" for r in rt["runelets"]]
        elif mtype == "LM_Mirror":
            target = lore.templates.get(m.get("templateFilter"))
            if target:
                lines.append(f"lists pages of template: {target['name']}")
        lines.append("")
    lists = lore.data.get("inspirationLists") or []
    if lists:
        lines += ["## Inspiration lists (whole file)"]
        lines += [f"- {l.get('name')}: {', '.join(map(str, l.get('items', [])[:12]))}" for l in lists]
    return "\n".join(lines).rstrip()


def _ordered_modules(template: dict) -> list[dict]:
    return sorted(template.get("usedModules", []), key=lambda m: (m.get("positionYMin", 0), m.get("positionXMin", 0)))


def lore_page(lore: Lore, ref: str) -> str:
    page = find_one(lore.pages, ref, lambda p: p["name"], "Lore page")
    ctx = Context(lore=lore)
    tmpl = lore.template_of(page)
    lines = [f"# {page['name']}", "", f"template: {tmpl['name'] if tmpl else '—'} · id: {page['idHash']}", ""]

    content = {m.get("relatedModuleId"): m for m in page.get("pageContent", [])}
    order = [m["idHash"] for m in _ordered_modules(tmpl)] if tmpl else []
    order += [k for k in content if k not in order]
    for mid in order:
        tm = lore.template_modules.get(mid, {})
        pm = content.get(mid)
        mtype = tm.get("typeCodeModule", "")
        header = (pm or {}).get("header") or tm.get("header") or short_type(mtype)
        if mtype == "LM_Mirror":
            links = [ctx.name_of_id(i) for i in page.get("mirrorLinksId") or []]
            if links:
                lines += [f"## {header}", *[f"- [[{x}]]" for x in links], ""]
            continue
        if not pm:
            continue
        if "body" in pm:
            body = html_to_text(pm.get("body"), ctx.label)
            if body:
                lines += [f"## {header}", body, ""]
        elif pm.get("runeletContent"):
            vals = []
            for rv in pm["runeletContent"]:
                label = lore.runelets.get(rv.get("relatedRuneletId"), {}).get("label", "?")
                v = str(rv.get("value") or "")
                kind, _, rid = v.partition("/")
                if kind == "lorePage" and rid:
                    v = f"[[{ctx.label(kind, rid) or 'missing page'}]]"
                if v:
                    vals.append(f"- {label}: {v}")
            if vals:
                lines += [f"## {header}", *vals, ""]
        elif pm.get("visualContent"):
            img = lore.images.get(pm["visualContent"].get("relatedImage"), {})
            lines += [f"## {header}", f"[image: {img.get('displayedName', '?')}]", ""]

    lines += _backlink_lines(ctx, lore.backlinks, page["idHash"])
    return "\n".join(lines).rstrip()


# --- search ----------------------------------------------------------------

def search(docs: list[Tome | Lore], query: str, ctx_for, limit: int = 20) -> str:
    """Search page names and text. ``ctx_for(doc)`` returns a Context for link labels."""
    key = normalize(query)
    if not key:
        raise ValueError("Empty query")
    hits: list[tuple[int, str]] = []
    for doc in docs:
        ctx = ctx_for(doc)
        texts: dict[str, list[str]] = defaultdict(list)
        for owner, html in doc.html_fields():
            texts[owner].append(html)
        if isinstance(doc, Tome):
            entries = [(p["idHash"], p["pageName"], short_type(p["type"])) for p in doc.all_pages.values()]
            entries += [(a["idHash"], f"{a['type']} arcane", "Arcane") for a in doc.arcanes.values()]
        else:
            entries = [(p["idHash"], p["name"], (doc.template_of(p) or {}).get("name", "Lore")) for p in doc.pages.values()]
        for pid, name, typ in entries:
            in_name = key in normalize(name)
            snippet = ""
            for html in texts.get(pid, []):
                if not html:
                    continue
                txt = html_to_text(html, ctx.label).replace("\n", " ")
                i = normalize(txt).find(key)
                if i >= 0:
                    snippet = "…" + txt[max(0, i - 80): i + len(query) + 80] + "…"
                    break
            if in_name or snippet:
                score = 0 if in_name else 1
                line = f"- [{doc.kind} {doc.name}] {name} ({typ}, {pid[:8]})"
                if snippet:
                    line += f"\n  {snippet}"
                hits.append((score, line))
    if not hits:
        return f"No match for {query!r}."
    hits.sort(key=lambda h: h[0])
    shown = hits[:limit]
    more = f"\n\n({len(hits) - limit} more results not shown; raise `limit` or refine the query.)" if len(hits) > limit else ""
    return f"# Results for {query!r} ({len(hits)})\n\n" + "\n".join(h[1] for h in shown) + more
