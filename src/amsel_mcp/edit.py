"""Editing operations on Tome and Lore files.

Each operation reads the file fresh from disk (never the read cache), applies the
change to the JSON, then saves through :mod:`writer` (app check, backup, atomic write).
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import render
from .archive import read_data_json
from .compose import text_to_html
from .model import Lore, PageNotFound, Tome, find_one
from .text import normalize
from .workspace import Workspace
from .writer import WriteRefused, ensure_app_closed, file_stamp, save

DATA_PAGE_TYPES = {
    "character": "TDP_Character", "personnage": "TDP_Character", "pnj": "TDP_Character",
    "location": "TDP_Location", "lieu": "TDP_Location",
    "object": "TDP_Object", "objet": "TDP_Object",
    "organization": "TDP_Organization", "organisation": "TDP_Organization", "faction": "TDP_Organization",
    "player": "TDP_Player", "joueur": "TDP_Player",
    "fable": "TDP_Fable",
}
STORY_PAGE_TYPES = {"scene": "TSP_Scene", "scène": "TSP_Scene", "chapter": "TSP_Chapter", "chapitre": "TSP_Chapter"}
CONTAINER_TYPES = {"TSP_Story", "TSP_ChapterFlow", "TSP_Chapter"}


def new_id() -> str:
    return str(uuid.uuid4())


def _cover() -> dict:
    return {"idHash": new_id(), "relatedTheme": "current", "themeImageIndex": random.randint(0, 3), "display": "fill", "caption": ""}


def _text_subpage(title: str, content: str) -> dict:
    return {
        "idHash": new_id(),
        "type": "text",
        "title": title,
        "contentByType": {
            "text": {"module": {"title": title, "content": content}},
            "checker": {"modules": [{"title": "Title", "content": ""} for _ in range(4)]},
            "gallery": {"displayType": "grid", "images": []},
        },
    }


MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _image_kind(raw: bytes) -> str | None:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def read_image(image_path: str) -> tuple[bytes, str, str]:
    """Load a local image file: (bytes, extension, default display name)."""
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise ValueError(f"No image file at {path}.")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError(f"{path.name} is larger than {MAX_IMAGE_BYTES // 2**20} MB.")
    raw = path.read_bytes()
    ext = _image_kind(raw)
    if not ext:
        raise ValueError(f"{path.name} is not a PNG, JPEG, WebP or GIF image.")
    return raw, ext, path.stem


def add_image(s: Session, image_path: str, name: str | None = None, folder: str | None = None) -> str:
    """Register an image in the file's image library and stage its bytes. Returns its id."""
    raw, ext, stem = read_image(image_path)
    folders = s.data.setdefault("imageFolders", [])
    now = int(time.time())
    if folder:
        target = next((f for f in folders if not f.get("isRootFolder") and normalize(f.get("name", "")) == normalize(folder)), None)
        if target is None:
            target = {"idHash": new_id(), "name": folder.strip(), "isRootFolder": False, "creationTimestamp": now,
                      "index": max([f.get("index", 0) for f in folders] + [0]) + 1}
            folders.append(target)
    else:
        target = next((f for f in folders if f.get("isRootFolder")), None)
        if target is None:
            target = {"idHash": new_id(), "name": "/", "index": -1, "isRootFolder": True, "creationTimestamp": now}
            folders.insert(0, target)
    img_id = new_id()
    s.data.setdefault("importedImages", []).append({
        "idHash": img_id, "optimized": True, "extension": ext, "displayedName": (name or stem).strip(),
        "index": -1, "isFavorite": False, "folderId": target["idHash"], "creationTimestamp": now,
    })
    s.files[f"img/{img_id}.{ext}"] = raw
    return img_id


def _join(old: str, new: str, append: bool) -> str:
    return (old or "") + new if append else new


def _type_code(value: str, table: dict[str, str], what: str) -> str:
    key = normalize(value)
    for name, code in table.items():
        if normalize(name) == key or normalize(code) == key or normalize(code.split("_", 1)[1]) == key:
            return code
    choices = sorted({c.split("_", 1)[1] for c in table.values()})
    raise ValueError(f"Unknown {what} {value!r}. Use one of: {', '.join(choices)}")


@dataclass
class Session:
    """A file opened for editing: fresh data + the on-disk stamp it was read at."""

    path: Path
    data: dict
    stamp: tuple[int, int]
    files: dict[str, bytes] = field(default_factory=dict)  # new archive members, e.g. images

    def commit(self) -> Path:
        return save(self.path, self.data, self.stamp, self.files)


class Editor:
    def __init__(self, ws: Workspace):
        self.ws = ws

    def _open(self, ref: str, kind: str) -> Session:
        path = self.ws.resolve_path(ref, kind)
        ensure_app_closed(path)  # fail fast, before doing any work
        stamp = file_stamp(path)
        return Session(path, read_data_json(path), stamp)

    # --- link resolution ---------------------------------------------------
    @staticmethod
    def _finder(tome: Tome | None, lore: Lore | None):
        cands: list[tuple[str, str]] = []  # (name, "kind/id")
        if tome:
            cands += [(p["pageName"], f"index/{i}") for i, p in tome.data_pages.items()]
            cands += [(p["pageName"], f"storyPage/{i}") for i, p in tome.story_pages.items()]
        if lore:
            cands += [(p["name"], f"lorePage/{i}") for i, p in lore.pages.items()]

        def find(name: str) -> str:
            key = normalize(name)
            exact = [c for c in cands if normalize(c[0]) == key]
            hits = exact or [c for c in cands if key in normalize(c[0])]
            if len(hits) == 1:
                return hits[0][1]
            if not hits:
                raise ValueError("no page with this name")
            return_names = ", ".join(sorted({h[0] for h in hits})[:8])
            raise ValueError(f"ambiguous, matches: {return_names}")

        return find

    def _tome_ctx(self, s: Session):
        tome = Tome(s.path, s.data)
        lore = self.ws.linked_lore(tome)
        return tome, lore, self._finder(tome, lore)

    def _done(self, s: Session, rendered_after) -> str:
        bak = s.commit()
        return f"{rendered_after()}\n\n---\nSaved {s.path.name}. Backup of the previous version: {bak}"

    # --- Tome ----------------------------------------------------------------
    def create_tome_data_page(self, tome_ref: str, name: str, page_type: str, summary: str = "",
                              sections: dict[str, str] | None = None) -> str:
        s = self._open(tome_ref, "tome")
        tome, lore, find = self._tome_ctx(s)
        code = _type_code(page_type, DATA_PAGE_TYPES, "data page type")
        name = name.strip()
        if not name:
            raise ValueError("A page name is required.")
        if any(normalize(p["pageName"]) == normalize(name) for p in tome.data_pages.values()):
            raise WriteRefused(f"A data page named {name!r} already exists; use update_tome_page instead.")
        page = {
            "idHash": new_id(), "coverImage": _cover(), "summary": text_to_html(summary, find),
            "pageName": name, "isFavorite": False, "type": code, "hideCoverImage": False,
            "relations": [], "subPages": [_text_subpage(t.strip(), text_to_html(txt, find)) for t, txt in (sections or {}).items()],
            "aliases": [], "isPlayer": False,
        }
        s.data.setdefault("dataPages", []).append(page)
        s.data.setdefault("dataPagesOrder", []).append({"idHash": page["idHash"], "type": "item"})
        return self._done(s, lambda: render.tome_page(Tome(s.path, s.data), lore, page["idHash"]))

    def create_tome_story_page(self, tome_ref: str, parent: str, name: str, page_type: str = "Scene",
                               summary: str = "", content: str = "") -> str:
        s = self._open(tome_ref, "tome")
        tome, lore, find = self._tome_ctx(s)
        code = _type_code(page_type, STORY_PAGE_TYPES, "story page type")
        par = find_one(tome.story_pages, parent, lambda p: p["pageName"], "parent story page")
        if par["type"] not in CONTAINER_TYPES:
            raise WriteRefused(f"{par['pageName']!r} is a {par['type']}: a new page must go under a story, chapter flow or chapter.")
        if code == "TSP_Chapter" and par["type"] == "TSP_Chapter":
            raise WriteRefused("A chapter cannot contain another chapter; choose a story or chapter flow as parent.")
        if content and code != "TSP_Scene":
            raise ValueError("Only scenes have a content field; put chapter text in `summary`.")
        page = {
            "idHash": new_id(), "coverImage": _cover(), "summary": text_to_html(summary, find),
            "pageName": name.strip(), "type": code, "parentId": par["idHash"], "pageStates": [], "aliases": [],
        }
        if code == "TSP_Scene":
            page["content"] = text_to_html(content, find)
        else:
            page["childrenIds"] = []
        s.data["storyPages"].append(page)
        par.setdefault("childrenIds", []).append(page["idHash"])
        return self._done(s, lambda: render.tome_page(Tome(s.path, s.data), lore, page["idHash"]))

    def update_tome_page(self, tome_ref: str, page_ref: str, new_name: str | None = None, summary: str | None = None,
                         content: str | None = None, sections: dict[str, str] | None = None, append: bool = False) -> str:
        s = self._open(tome_ref, "tome")
        tome, lore, find = self._tome_ctx(s)
        page = find_one(tome.all_pages, page_ref, lambda p: p["pageName"], "Tome page")
        is_story = page["idHash"] in tome.story_pages
        if not any(v is not None for v in (new_name, summary, content, sections)):
            raise ValueError("Nothing to change: give new_name, summary, content and/or sections.")
        if new_name is not None:
            pool = tome.story_pages if is_story else tome.data_pages
            if any(normalize(p["pageName"]) == normalize(new_name) for i, p in pool.items() if i != page["idHash"]):
                raise WriteRefused(f"Another page is already named {new_name!r}.")
            page["pageName"] = new_name.strip()
        if summary is not None:
            page["summary"] = _join(page.get("summary"), text_to_html(summary, find), append)
        if content is not None:
            if page.get("type") != "TSP_Scene":
                raise ValueError("Only scenes have a content field; use summary or sections.")
            page["content"] = _join(page.get("content"), text_to_html(content, find), append)
        if sections:
            if is_story:
                raise ValueError("Story pages have no sections; use summary or content.")
            subs = page.setdefault("subPages", [])
            for title, txt in sections.items():
                new_html = text_to_html(txt, find)
                sub = next((sp for sp in subs if normalize(sp.get("title", "")) == normalize(title)), None)
                if sub is None:
                    subs.append(_text_subpage(title.strip(), new_html))
                elif sub.get("type") != "text":
                    raise WriteRefused(f"Section {sub['title']!r} is a checklist; only text sections can be edited.")
                else:
                    mod = sub["contentByType"].setdefault("text", {}).setdefault("module", {"title": sub["title"]})
                    mod["content"] = _join(mod.get("content"), new_html, append)
        return self._done(s, lambda: render.tome_page(Tome(s.path, s.data), lore, page["idHash"]))

    def add_tome_note(self, tome_ref: str, text: str, session: str | None = None) -> str:
        s = self._open(tome_ref, "tome")
        tome = Tome(s.path, s.data)
        if not tome.sessions:
            raise WriteRefused("This Tome has no game session to attach the note to.")
        if session:
            matches = [sid for sid, label in tome.sessions.items() if normalize(label) == normalize(session) or sid.startswith(session)]
            if len(matches) != 1:
                raise ValueError(f"Unknown session {session!r}. Sessions: {', '.join(tome.sessions.values())}")
            sid = matches[0]
        else:
            sid = s.data.get("loadedSessionId") if s.data.get("loadedSessionId") in tome.sessions else list(tome.sessions)[-1]
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        s.data.setdefault("notes", []).append({"idHash": new_id(), "relatedSessionId": sid, "content": text.strip(), "dateSys": now})
        return self._done(s, lambda: render.tome_notes(Tome(s.path, s.data)))

    def set_tome_page_image(self, tome_ref: str, page_ref: str, image_path: str, caption: str | None = None,
                            image_name: str | None = None, folder: str | None = None) -> str:
        s = self._open(tome_ref, "tome")
        tome = Tome(s.path, s.data)
        pages = {**tome.data_pages, **tome.story_pages}
        page = find_one(pages, page_ref, lambda p: p["pageName"], "Tome page")
        img_id = add_image(s, image_path, image_name or page["pageName"], folder)
        old = page.get("coverImage") or {}
        page["coverImage"] = {"idHash": old.get("idHash") or new_id(), "relatedImage": img_id, "display": "fit",
                              "caption": old.get("caption", "") if caption is None else caption}
        lore = self.ws.linked_lore(tome)
        return self._done(s, lambda: render.tome_page(Tome(s.path, s.data), lore, page["idHash"]))

    # --- Lore ----------------------------------------------------------------
    @staticmethod
    def _text_modules(lore: Lore, template: dict) -> dict[str, dict]:
        mods = [m for m in template.get("usedModules", []) if m.get("typeCodeModule") == "LM_Standard_Text"]
        return {normalize(m.get("header") or ""): m for m in mods}

    def _fill_fields(self, lore: Lore, template: dict, page: dict, fields: dict[str, str], append: bool, find) -> None:
        mods = self._text_modules(lore, template)
        content = {c.get("relatedModuleId"): c for c in page["pageContent"]}
        by_id = {m["idHash"]: m for m in mods.values()}
        for c in page["pageContent"]:  # a page may rename a module ("Description" shown as "Histoire")
            if c.get("header") and c.get("relatedModuleId") in by_id:
                mods.setdefault(normalize(c["header"]), by_id[c["relatedModuleId"]])
        unknown = [h for h in fields if normalize(h) not in mods]
        if unknown:
            avail = ", ".join(m.get("header") or "—" for m in mods.values())
            raise ValueError(f"Unknown field(s) {unknown} for template {template['name']!r}. Text fields: {avail}")
        for header, txt in fields.items():
            mod = mods[normalize(header)]
            c = content.get(mod["idHash"])
            if c is None:
                c = {"idHash": new_id(), "relatedModuleId": mod["idHash"], "header": "", "body": ""}
                page["pageContent"].append(c)
            c["body"] = _join(c.get("body"), text_to_html(txt, find), append)

    def create_lore_page(self, lore_ref: str, template: str, name: str, fields: dict[str, str] | None = None) -> str:
        s = self._open(lore_ref, "lore")
        lore = Lore(s.path, s.data)
        find = self._finder(None, lore)
        tmpl = find_one(lore.templates, template, lambda t: t["name"], "template")
        name = name.strip()
        if not name:
            raise ValueError("A page name is required.")
        if any(normalize(p["name"]) == normalize(name) for p in lore.pages.values()):
            raise WriteRefused(f"A Lore page named {name!r} already exists; use update_lore_page instead.")
        runes = {rt["idHash"]: rt for rt in s.data.get("runeTemplates", [])}
        content = []
        for m in tmpl.get("usedModules", []):
            c = {"idHash": new_id(), "relatedModuleId": m["idHash"]}
            t = m.get("typeCodeModule")
            if t == "LM_Standard_Text":
                c.update(header="", body="")
            elif t == "LM_Rune":
                rt = runes.get(m.get("linkedModuleTemplateId"), {})
                c["runeletContent"] = [{"value": "", "relatedRuneletId": r["idHash"]} for r in rt.get("runelets", [])]
            content.append(c)
        page = {"idHash": new_id(), "name": name, "isFavorite": False, "pageContent": content,
                "templateId": tmpl["idHash"], "mirrorLinksId": []}
        self._fill_fields(lore, tmpl, page, fields or {}, False, find)
        s.data.setdefault("pages", []).append(page)
        return self._done(s, lambda: render.lore_page(Lore(s.path, s.data), page["idHash"]))

    def update_lore_page(self, lore_ref: str, page_ref: str, new_name: str | None = None,
                         fields: dict[str, str] | None = None, append: bool = False) -> str:
        s = self._open(lore_ref, "lore")
        lore = Lore(s.path, s.data)
        page = find_one(lore.pages, page_ref, lambda p: p["name"], "Lore page")
        if new_name is None and not fields:
            raise ValueError("Nothing to change: give new_name and/or fields.")
        if new_name is not None:
            if any(normalize(p["name"]) == normalize(new_name) for i, p in lore.pages.items() if i != page["idHash"]):
                raise WriteRefused(f"Another Lore page is already named {new_name!r}.")
            page["name"] = new_name.strip()
        if fields:
            tmpl = lore.template_of(page)
            if not tmpl:
                raise WriteRefused("This page has no template; its fields cannot be edited.")
            self._fill_fields(lore, tmpl, page, fields, append, self._finder(None, lore))
        return self._done(s, lambda: render.lore_page(Lore(s.path, s.data), page["idHash"]))

    def set_lore_page_image(self, lore_ref: str, page_ref: str, image_path: str, module: str | None = None,
                            caption: str | None = None, image_name: str | None = None, folder: str | None = None) -> str:
        s = self._open(lore_ref, "lore")
        lore = Lore(s.path, s.data)
        page = find_one(lore.pages, page_ref, lambda p: p["name"], "Lore page")
        tmpl = lore.template_of(page)
        mods = [m for m in (tmpl or {}).get("usedModules", []) if m.get("typeCodeModule") == "LM_Image"]
        if not mods:
            raise WriteRefused(f"The template of {page['name']!r} has no image module.")
        if module:
            mods = [m for m in mods if normalize(m.get("header") or "") == normalize(module)] or [None]
            if mods[0] is None:
                raise ValueError(f"No image module {module!r}. Image modules: "
                                 + ", ".join(m.get("header") or "—" for m in tmpl["usedModules"] if m.get("typeCodeModule") == "LM_Image"))
        elif len(mods) > 1:
            raise ValueError("This template has several image modules; choose one with module=: "
                             + ", ".join(m.get("header") or "—" for m in mods))
        mod = mods[0]
        img_id = add_image(s, image_path, image_name or page["name"], folder)
        c = next((c for c in page["pageContent"] if c.get("relatedModuleId") == mod["idHash"]), None)
        if c is None:
            c = {"idHash": new_id(), "relatedModuleId": mod["idHash"]}
            page["pageContent"].append(c)
        old = c.get("visualContent") or {}
        c["visualContent"] = {"idHash": old.get("idHash") or new_id(), "relatedImage": img_id, "display": "fit",
                              "caption": old.get("caption", "") if caption is None else caption}
        return self._done(s, lambda: render.lore_page(Lore(s.path, s.data), page["idHash"]))


__all__ = ["Editor", "PageNotFound", "WriteRefused"]
