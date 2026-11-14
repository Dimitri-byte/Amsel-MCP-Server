"""In-memory views of Tome and Lore projects, with lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from .text import extract_links, normalize


def short_type(t: str) -> str:
    """'TDP_Character' -> 'Character', 'LC_Cultural' -> 'Cultural'."""
    return t.split("_", 1)[1] if "_" in (t or "") else (t or "")


class PageNotFound(ValueError):
    pass


def find_one(items: dict[str, dict], ref: str, name_of, what: str) -> dict:
    """Find an item by id, id prefix (>= 6 chars), exact name, or unique partial name."""
    ref = (ref or "").strip()
    if not ref:
        raise PageNotFound(f"Empty {what} reference")
    if ref in items:
        return items[ref]
    if len(ref) >= 6:
        by_prefix = [v for k, v in items.items() if k.startswith(ref)]
        if len(by_prefix) == 1:
            return by_prefix[0]
    key = normalize(ref)
    exact = [v for v in items.values() if normalize(name_of(v)) == key]
    if len(exact) == 1:
        return exact[0]
    partial = exact or [v for v in items.values() if key in normalize(name_of(v))]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise PageNotFound(f"No {what} matches {ref!r}")
    names = ", ".join(f"{name_of(v)!r} ({v['idHash'][:8]})" for v in partial[:15])
    more = f" … and {len(partial) - 15} more" if len(partial) > 15 else ""
    raise PageNotFound(f"{len(partial)} {what}s match {ref!r}: {names}{more}. Use a more precise name or the id.")


@dataclass
class Tome:
    path: Path
    data: dict

    @property
    def kind(self) -> str:
        return "tome"

    @property
    def name(self) -> str:
        return self.data.get("storyName") or self.path.stem

    @cached_property
    def story_pages(self) -> dict[str, dict]:
        return {p["idHash"]: p for p in self.data.get("storyPages", [])}

    @cached_property
    def data_pages(self) -> dict[str, dict]:
        return {p["idHash"]: p for p in self.data.get("dataPages", [])}

    @cached_property
    def pointers(self) -> dict[str, dict]:
        return {p["idHash"]: p for p in self.data.get("pointers", [])}

    @cached_property
    def arcanes(self) -> dict[str, dict]:
        return {a["idHash"]: a for a in self.data.get("arcanes", [])}

    @cached_property
    def sessions(self) -> dict[str, str]:
        """session id -> display name."""
        out = {}
        for i, s in enumerate(self.data.get("gameSessions", []), 1):
            out[s["idHash"]] = s.get("sessionName") or f"Session {i}"
        return out

    @cached_property
    def all_pages(self) -> dict[str, dict]:
        return {**self.story_pages, **self.data_pages}

    @cached_property
    def data_page_order(self) -> list[str]:
        order = [o["idHash"] for o in self.data.get("dataPagesOrder", []) if o["idHash"] in self.data_pages]
        seen = set(order)
        return order + [k for k in self.data_pages if k not in seen]

    def roots(self) -> list[dict]:
        return [p for p in self.story_pages.values() if not p.get("parentId") or p["parentId"] not in self.story_pages]

    def children(self, page: dict) -> list[dict]:
        ids = list(page.get("childrenIds") or [])
        extra = [p["idHash"] for p in self.story_pages.values() if p.get("parentId") == page["idHash"] and p["idHash"] not in ids]
        return [self.story_pages[i] for i in ids + extra if i in self.story_pages]

    def html_fields(self) -> list[tuple[str, str]]:
        """(owner id, html) for every rich-text field, to build backlinks and search."""
        out = []
        for p in self.story_pages.values():
            out += [(p["idHash"], p.get("summary") or ""), (p["idHash"], p.get("content") or "")]
        for p in self.data_pages.values():
            out.append((p["idHash"], p.get("summary") or ""))
            for sp in p.get("subPages", []):
                out += [(p["idHash"], h) for h in subpage_html(sp)]
        for a in self.arcanes.values():
            out.append((a["idHash"], a.get("text") or ""))
            out += [(a["idHash"], r.get("commentary") or "") for r in a.get("results", [])]
        return out

    @cached_property
    def backlinks(self) -> dict[str, list[str]]:
        return _backlinks(self.html_fields())


def subpage_html(sp: dict) -> list[str]:
    cbt = sp.get("contentByType") or {}
    if sp.get("type") == "checker":
        return [m.get("content") or "" for m in (cbt.get("checker") or {}).get("modules", [])]
    if sp.get("type") == "text":
        return [((cbt.get("text") or {}).get("module") or {}).get("content") or ""]
    return []


@dataclass
class Lore:
    path: Path
    data: dict

    @property
    def kind(self) -> str:
        return "lorekit" if self.path.suffix.lower() == ".lorekit" else "lore"

    @property
    def name(self) -> str:
        return self.data.get("fileName") or self.data.get("name") or self.path.stem

    @cached_property
    def pages(self) -> dict[str, dict]:
        return {p["idHash"]: p for p in self.data.get("pages", [])}

    @cached_property
    def templates(self) -> dict[str, dict]:
        return {t["idHash"]: t for t in self.data.get("templates", [])}

    @cached_property
    def template_modules(self) -> dict[str, dict]:
        return {m["idHash"]: m for t in self.templates.values() for m in t.get("usedModules", [])}

    @cached_property
    def rune_templates(self) -> dict[str, dict]:
        """Rune templates by id, as ``{name, runelets: [{idHash, label, type}]}``.

        Older files (lastVer <= 17) store ``runeTemplates[].runelets``; newer ones
        (lastVer 23) store ``runeGroups[].runes``.
        """
        out = {rt["idHash"]: {"name": rt.get("name", ""), "runelets": rt.get("runelets", [])}
               for rt in self.data.get("runeTemplates", [])}
        for g in self.data.get("runeGroups", []):
            out[g["idHash"]] = {"name": g.get("name", ""), "runelets": g.get("runes", [])}
        return out

    @cached_property
    def runelets(self) -> dict[str, dict]:
        return {r["idHash"]: r for rt in self.rune_templates.values() for r in rt["runelets"]}

    def category_name(self, template: dict) -> str:
        """'LC_Cultural' -> 'Cultural'; custom categories (stored by id) -> their name."""
        cat = template.get("category", "")
        for c in self.data.get("customTemplateCategories", []):
            if c.get("idHash") == cat:
                return c.get("name", "")
        return short_type(cat)

    @cached_property
    def images(self) -> dict[str, dict]:
        return {i["idHash"]: i for i in self.data.get("importedImages", [])}

    def template_of(self, page: dict) -> dict | None:
        return self.templates.get(page.get("templateId"))

    def html_fields(self) -> list[tuple[str, str]]:
        out = []
        for p in self.pages.values():
            for m in p.get("pageContent", []):
                out.append((p["idHash"], m.get("body") or ""))
        return out

    @cached_property
    def backlinks(self) -> dict[str, list[str]]:
        bl = _backlinks(self.html_fields())
        for p in self.pages.values():  # rune values can point to pages too
            for m in p.get("pageContent", []):
                for rv in m.get("runeletContent") or []:
                    kind, _, ref = str(rv.get("value") or "").partition("/")
                    if kind == "lorePage" and ref and p["idHash"] not in bl.setdefault(ref, []):
                        bl[ref].append(p["idHash"])
        return bl


def _backlinks(fields: list[tuple[str, str]]) -> dict[str, list[str]]:
    bl: dict[str, list[str]] = {}
    for owner, html in fields:
        for _kind, ref in extract_links(html):
            lst = bl.setdefault(ref, [])
            if owner not in lst and owner != ref:
                lst.append(owner)
    return bl


@dataclass
class Context:
    """A Tome and/or Lore opened together so cross-links can be resolved."""

    tome: Tome | None = None
    lore: Lore | None = None
    _arcane_depth: int = field(default=0, repr=False)

    def label(self, kind: str, ref: str) -> str | None:
        t, l = self.tome, self.lore
        if kind == "lorePage":
            p = l.pages.get(ref) if l else None
            return p["name"] if p else None
        if kind == "index":
            if t and ref in t.data_pages:
                return t.data_pages[ref]["pageName"]
            if t and ref in t.pointers:
                return t.pointers[ref].get("label")
            return None
        if kind == "storyPage":
            p = t.story_pages.get(ref) if t else None
            return p["pageName"] if p else None
        if kind == "arcane":
            a = t.arcanes.get(ref) if t else None
            if not a:
                return None
            if self._arcane_depth:
                return f"{a['type']} arcane"
            from .text import html_to_text

            self._arcane_depth += 1
            try:
                txt = html_to_text(a.get("text"), self.label).replace("\n", " ").replace("[[", "").replace("]]", "")
            finally:
                self._arcane_depth -= 1
            return f"{a['type']}: {txt[:80]}{'…' if len(txt) > 80 else ''}"
        return None

    def name_of_id(self, ref: str) -> str:
        for kind in ("storyPage", "index", "lorePage", "arcane"):
            lab = self.label(kind, ref)
            if lab:
                return lab
        return ref[:8]
