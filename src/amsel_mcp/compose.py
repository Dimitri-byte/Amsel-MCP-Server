"""Turn the light Markdown the model writes into Amsel's rich-text HTML.

Supported: paragraphs (one per line, blank lines kept), ``**bold**``, ``*italic*``,
``### `` / ``#### `` headings, ``---`` separators, ``- `` / ``1. `` lists (indent by
2 spaces to nest), ``> `` quotes, and ``[[Page name]]`` links to existing pages.
"""

from __future__ import annotations

import html
import re
from typing import Callable

# name -> "kind/id"; raises ValueError when the name is unknown or ambiguous
LinkFinder = Callable[[str], str]

P = '<p class="text-body">{}</p>'
_LINK = re.compile(r"\[\[([^\[\]]+)\]\]")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_ITALIC = re.compile(r"(?<![\*\w])\*(?=\S)(.+?)(?<=\S)\*(?![\*\w])")
_UL = re.compile(r"^(\s*)[-*•]\s+(.*)$")
_OL = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_HEADING = re.compile(r"^\s*(#{1,6})\s+(.*)$")
_RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_LIST_CLASS = {"ul": "list-disc pl-5", "ol": "list-decimal"}


def _list_item(line: str) -> tuple[int, str, str] | None:
    """(indent, 'ul'|'ol', text) for a list line, else None."""
    if _RULE.match(line):
        return None
    for rx, tag in ((_UL, "ul"), (_OL, "ol")):
        m = rx.match(line)
        if m:
            return len(m.group(1).expandtabs(2)), tag, m.group(2)
    return None


def _build_list(items: list[tuple[int, str, str]], i: int, fmt) -> tuple[str, int]:
    """Render items[i:] at the indent of items[i]; deeper items nest inside the previous <li>."""
    indent, tag, _ = items[i]
    parts: list[str] = []
    while i < len(items) and items[i][0] >= indent:
        if items[i][0] > indent:  # nested list belongs to the previous item
            sub, i = _build_list(items, i, fmt)
            parts[-1] = parts[-1][: -len("</li>")] + sub + "</li>"
            continue
        if items[i][1] != tag:  # same level, other list type: close this list
            break
        parts.append(f"<li>{P.format(fmt(items[i][2]))}</li>")
        i += 1
    return f'<{tag} class="{_LIST_CLASS[tag]}">{"".join(parts)}</{tag}>', i


def _inline(text: str, find: LinkFinder | None, errors: list[str]) -> str:
    """Format one line. Links become placeholders first so **[[x]]** keeps its emphasis."""
    links: list[str] = []

    def stash(m: re.Match) -> str:
        name = m.group(1).strip()
        tag = ""
        if find is None:
            errors.append(f"[[{name}]]: links are not available here")
        else:
            try:
                tag = f'<tag-component id="{find(name)}"></tag-component>'
            except ValueError as exc:
                errors.append(f"[[{name}]]: {exc}")
        links.append(tag)
        return f"\x00{len(links) - 1}\x00"

    out = _format(_LINK.sub(stash, text))
    return re.sub("\x00(\\d+)\x00", lambda m: links[int(m.group(1))], out)


def _format(text: str) -> str:
    out = html.escape(text, quote=False)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC.sub(r"<em>\1</em>", out)
    return out


def text_to_html(text: str, find: LinkFinder | None = None) -> str:
    """Convert text to Amsel HTML. Raises ValueError listing every unresolvable link."""
    text = (text or "").replace("\r\n", "\n").strip("\n")
    if not text.strip():
        return ""
    errors: list[str] = []
    out: list[str] = []
    lines = text.split("\n")
    i = 0
    def fmt(t: str) -> str:
        return _inline(t.strip(), find, errors)

    while i < len(lines):
        line = lines[i]
        if _list_item(line):
            items = []
            while i < len(lines) and _list_item(lines[i]):
                items.append(_list_item(lines[i]))
                i += 1
            base = min(it[0] for it in items)
            items = [(ind - base, tag, t) for ind, tag, t in items]
            j = 0
            while j < len(items):
                html_list, j = _build_list(items, j, fmt)
                out.append(html_list)
        elif _RULE.match(line):
            out.append('<hr class="">')
            i += 1
        elif _HEADING.match(line):
            level = len(_HEADING.match(line).group(1))
            out.append(f'<h{4 if level >= 4 else 3} class="text-body">{fmt(_HEADING.match(line).group(2))}</h{4 if level >= 4 else 3}>')
            i += 1
        elif line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(P.format(fmt(lines[i].lstrip()[1:])))
                i += 1
            out.append(f"<blockquote>{''.join(quote)}</blockquote>")
        else:
            out.append(P.format(fmt(line)))
            i += 1
    if errors:
        raise ValueError("Unresolved links — nothing was written:\n- " + "\n- ".join(errors))
    return "".join(out)
