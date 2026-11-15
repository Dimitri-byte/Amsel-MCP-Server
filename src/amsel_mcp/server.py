"""MCP server exposing Amsel Suite (Tome & Lore) files.

Read tools are always available. Write tools are registered only when the
environment variable ``AMSEL_WRITE=1`` is set.
"""

from __future__ import annotations

import functools
import os
from datetime import datetime

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import render
from .edit import Editor
from .archive import kind_of
from .model import Context, Lore, Tome
from .workspace import Workspace

WRITE_ENABLED = os.environ.get("AMSEL_WRITE") == "1"

_WRITE_HELP = (
    " Write tools are enabled: they create or update pages and notes. Text uses light Markdown "
    "(one paragraph per line, **bold**, *italic*, '### '/'#### ' headings, '---' separators, '- ' or "
    "'1. ' lists nested by 2-space indent, '> ' quotes) and [[Page name]] links to "
    "existing pages. In scene content, a line '[[choice: question]]' (or destiny, role, count, '[[options: text | a | b]]') creates an arcane. Images come from local files (set_lore_page_image, set_tome_page_image). Every write is refused while the Tome/Lore app is open, and a backup is kept in "
    ".amsel-backups/ next to the file. Read the page first, and confirm with the user before writing."
    if WRITE_ENABLED else " Write tools are disabled (set AMSEL_WRITE=1 to enable them)."
)

mcp = MCPServer(
    "amsel",
    instructions=(
        "Access to Amsel Suite tabletop-RPG files. A Tome (.tome) holds a "
        "campaign: a story tree (story/chapter/scene pages), data pages (characters, "
        "locations, objects, organizations, players), arcanes (planned choices/destinies "
        "and their per-session results) and session notes. A Lore (.lore) holds a world: "
        "pages built from templates. A Lore kit (.lorekit) holds only templates, to be imported in "
        "a Lore; read it with list_lore_templates / read_lore_template. Links between pages appear as [[Page name]]. "
        "Start with list_amsel_files, then use outline/list tools before reading pages. "
        "Files and pages can be referenced by name, partial name or id." + _WRITE_HELP
    ),
)
ws = Workspace()
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)


def _register(fn, annotations: ToolAnnotations):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:  # bad reference or refused write: tell the model what went wrong
            raise ToolError(str(exc)) from exc

    mcp.tool(annotations=annotations)(wrapper)


def tool(fn):
    """Register ``fn`` as a read-only tool. Returns ``fn`` unchanged so it can be called directly."""
    _register(fn, READ_ONLY)
    return fn


def write_tool(fn):
    """Register ``fn`` as a write tool, only when AMSEL_WRITE=1. Always returns ``fn`` unchanged."""
    if WRITE_ENABLED:
        _register(fn, WRITES)
    return fn


def _ctx_for(doc: Tome | Lore) -> Context:
    if isinstance(doc, Tome):
        return Context(tome=doc, lore=ws.linked_lore(doc))
    return Context(lore=doc)


@tool
def list_amsel_files() -> list[dict]:
    """List the Tome (.tome), Lore (.lore) and Lore kit (.lorekit) files found in the configured folders."""
    out = []
    for p in ws.discover():
        st = p.stat()
        item = {
            "name": p.stem,
            "kind": kind_of(p),
            "path": str(p),
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
            "size_kb": st.st_size // 1024,
        }
        try:
            doc = ws.open(str(p))
            if isinstance(doc, Tome):
                lore = ws.linked_lore(doc)
                item.update(story_pages=len(doc.story_pages), data_pages=len(doc.data_pages),
                            arcanes=len(doc.arcanes), linked_lore=str(lore.path) if lore else None)
            elif doc.kind == "lorekit":
                item.update(title=doc.name, templates=len(doc.templates), rune_templates=len(doc.rune_templates))
            else:
                item.update(pages=len(doc.pages), templates=len(doc.templates))
        except Exception as exc:  # keep listing even if one file is broken
            item["error"] = str(exc)
        out.append(item)
    return out


@tool
def tome_outline(tome: str, with_summaries: bool = False) -> str:
    """Show a Tome's story tree (story → chapters → scenes) with ribbons and per-session states.

    Args:
        tome: Tome file name, partial name or path.
        with_summaries: also print each page's summary (longer output).
    """
    return render.tome_outline(ws.tome(tome), with_summaries)


@tool
def list_tome_data_pages(tome: str, page_type: str | None = None) -> str:
    """List a Tome's data pages (characters, locations, objects, organizations, players…), grouped by type.

    Args:
        tome: Tome file name, partial name or path.
        page_type: optional filter, e.g. "Character", "Location", "Object", "Organization", "Player".
    """
    return render.tome_data_pages(ws.tome(tome), page_type)


@tool
def read_tome_page(tome: str, page: str) -> str:
    """Read one Tome page (story page or data page) as Markdown, with links resolved and backlinks.

    Args:
        tome: Tome file name, partial name or path.
        page: page name, partial name, or id (or id prefix).
    """
    t = ws.tome(tome)
    return render.tome_page(t, ws.linked_lore(t), page)


@tool
def list_tome_arcanes(tome: str, arcane_type: str | None = None) -> str:
    """List a Tome's arcanes (choice, destiny, role, options, count) with their results per session.

    Args:
        tome: Tome file name, partial name or path.
        arcane_type: optional filter: "choice", "destiny", "role", "options" or "count".
    """
    t = ws.tome(tome)
    return render.tome_arcanes(t, ws.linked_lore(t), arcane_type)


@tool
def read_tome_notes(tome: str) -> str:
    """Read a Tome's session notes."""
    return render.tome_notes(ws.tome(tome))


@tool
def list_lore_pages(lore: str, template: str | None = None) -> str:
    """List a Lore's pages grouped by template.

    Args:
        lore: Lore file name, partial name or path.
        template: optional template-name filter (partial, case/accent-insensitive).
    """
    return render.lore_pages(ws.lore(lore), template)


@tool
def list_lore_templates(lore: str) -> str:
    """List the templates of a Lore or Lore kit (.lorekit): category, number of pages, modules.

    Args:
        lore: Lore or Lore kit file name, partial name or path.
    """
    return render.lore_templates(ws.lore(lore))


@tool
def read_lore_template(lore: str, template: str) -> str:
    """Read one template of a Lore or Lore kit: modules in layout order, rune fields, mirror targets.

    Args:
        lore: Lore or Lore kit file name, partial name or path.
        template: template name, partial name, or id (or id prefix).
    """
    return render.lore_template(ws.lore(lore), template)


@tool
def read_lore_page(lore: str, page: str) -> str:
    """Read one Lore page as Markdown (modules in template order, links resolved, backlinks).

    Args:
        lore: Lore file name, partial name or path.
        page: page name, partial name, or id (or id prefix).
    """
    return render.lore_page(ws.lore(lore), page)


@tool
def search_amsel(query: str, file: str | None = None, limit: int = 20) -> str:
    """Search page names and text (case- and accent-insensitive).

    Args:
        query: text to look for.
        file: optional Tome/Lore name or path; when a Tome is given its linked Lore is searched too.
            When omitted, every known file is searched.
        limit: maximum number of results.
    """
    if file:
        doc = ws.open(file)
        docs: list[Tome | Lore] = [doc]
        if isinstance(doc, Tome):
            lore = ws.linked_lore(doc)
            if lore:
                docs.append(lore)
    else:
        docs = [ws.open(str(p)) for p in ws.discover()]
    return render.search(docs, query, _ctx_for, limit)


# --- write tools (AMSEL_WRITE=1) -------------------------------------------------

@write_tool
def create_tome_data_page(tome: str, name: str, page_type: str, summary: str = "",
                          sections: dict[str, str] | None = None) -> str:
    """Create a data page (character, location, object, organization, player, fable) in a Tome.

    Args:
        tome: Tome file name, partial name or path.
        name: page name, e.g. "PNJ : Mirelle" (must not already exist).
        page_type: Character, Location, Object, Organization, Player or Fable (French names accepted).
        summary: optional summary text.
        sections: optional text sections, {title: text}, e.g. {"Summary": "...", "Impact on the story": "..."}; use the section titles the Tome already uses.
    """
    return Editor(ws).create_tome_data_page(tome, name, page_type, summary, sections)


@write_tool
def create_tome_story_page(tome: str, parent: str, name: str, page_type: str = "Scene",
                           summary: str = "", content: str = "") -> str:
    """Create a scene or chapter in a Tome's story tree, as the last child of `parent`.

    Args:
        tome: Tome file name, partial name or path.
        parent: the story, chapter flow or chapter that will contain the new page.
        name: page name.
        page_type: "Scene" or "Chapter".
        summary: optional summary text.
        content: optional scene text (scenes only). A line holding only [[choice: question]], [[destiny: event]], [[role: task]], [[options: text | option 1 | option 2]] or [[count: label]] inserts a new arcane; [[choice#1041e488: …]] (id as shown by read_tome_page) keeps an existing one.
    """
    return Editor(ws).create_tome_story_page(tome, parent, name, page_type, summary, content)


@write_tool
def update_tome_page(tome: str, page: str, new_name: str | None = None, summary: str | None = None,
                     content: str | None = None, sections: dict[str, str] | None = None,
                     append: bool = False) -> str:
    """Rename a Tome page or change its text. Only the fields you pass are changed.

    Args:
        tome: Tome file name, partial name or path.
        page: page name, partial name or id.
        new_name: new page name.
        summary: new summary text.
        content: new scene text (scenes only); arcane lines as in create_tome_story_page. When replacing content, keep the existing arcanes' [[type#id: …]] lines or they are detached from the scene.
        sections: data pages only, {section title: text}; a missing text section is created.
        append: add the text after the existing text instead of replacing it.
    """
    return Editor(ws).update_tome_page(tome, page, new_name, summary, content, sections, append)


@write_tool
def add_tome_session_note(tome: str, text: str, session: str | None = None) -> str:
    """Add a session note to a Tome.

    Args:
        tome: Tome file name, partial name or path.
        text: note text (plain text).
        session: session name (e.g. "Session 1"); defaults to the session currently loaded in Tome.
    """
    return Editor(ws).add_tome_note(tome, text, session)


@write_tool
def create_lore_page(lore: str, template: str, name: str, fields: dict[str, str] | None = None) -> str:
    """Create a Lore page from a template.

    Args:
        lore: Lore file name, partial name or path.
        template: template name (see list_lore_templates).
        name: page name (must not already exist).
        fields: optional text fields, {module header: text}, e.g. {"DESCRITION": "..."}.
    """
    return Editor(ws).create_lore_page(lore, template, name, fields)


@write_tool
def update_lore_page(lore: str, page: str, new_name: str | None = None,
                     fields: dict[str, str] | None = None, append: bool = False) -> str:
    """Rename a Lore page or change its text fields. Only the fields you pass are changed.

    Args:
        lore: Lore file name, partial name or path.
        page: page name, partial name or id.
        new_name: new page name.
        fields: {module header: text} for the template's text modules.
        append: add the text after the existing text instead of replacing it.
    """
    return Editor(ws).update_lore_page(lore, page, new_name, fields, append)


@write_tool
def set_lore_page_image(lore: str, page: str, image_path: str, module: str | None = None,
                        caption: str | None = None, image_name: str | None = None, folder: str | None = None) -> str:
    """Put an image in a Lore page's image module (replaces the image shown there).

    The image is added to the Lore's image library; any previous image stays in the library.

    Args:
        lore: Lore file name, partial name or path.
        page: page name, partial name or id.
        image_path: path of a local PNG, JPEG, WebP or GIF file (download it first if it is online).
        module: image module header, needed only when the template has several image modules.
        caption: caption shown under the image (keeps the current one if omitted).
        image_name: name in the image library (default: the page name).
        folder: image-library folder, created if missing (default: the root folder).
    """
    return Editor(ws).set_lore_page_image(lore, page, image_path, module, caption, image_name, folder)


@write_tool
def set_tome_page_image(tome: str, page: str, image_path: str, caption: str | None = None,
                        image_name: str | None = None, folder: str | None = None) -> str:
    """Set the cover image of a Tome page (data page or story page).

    Args:
        tome: Tome file name, partial name or path.
        page: page name, partial name or id.
        image_path: path of a local PNG, JPEG, WebP or GIF file (download it first if it is online).
        caption: caption shown with the image (keeps the current one if omitted).
        image_name: name in the image library (default: the page name).
        folder: image-library folder, created if missing (default: the root folder).
    """
    return Editor(ws).set_tome_page_image(tome, page, image_path, caption, image_name, folder)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
