"""Convert Amsel's rich-text HTML into readable Markdown-ish text."""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser
from typing import Callable, Optional

# (kind, id) -> human label, or None when the target does not exist.
Resolver = Callable[[str, str], Optional[str]]

_LINK_RE = re.compile(
    r'<tag-component\s+id=\\?"([A-Za-z]+)/([\w-]+)'
    r'|<(?:destiny|intrigue)-component\s+id(?:hash)?=\\?"([\w-]+)'
)
_BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}


def extract_links(html: str) -> list[tuple[str, str]]:
    """Return every (kind, id) referenced by an HTML fragment."""
    out = []
    for kind, ref, arcane in _LINK_RE.findall(html or ""):
        out.append(("arcane", arcane) if arcane else (kind, ref))
    return out


class _Converter(HTMLParser):
    def __init__(self, resolve: Resolver | None):
        super().__init__(convert_charrefs=True)
        self.resolve = resolve
        self.out: list[str] = []
        self.lists: list[list] = []  # [tag, counter]
        self.href: str | None = None
        self.link_text_start = 0
        self.marks: list[int] = []  # positions in self.out of open **/* markers
        self.in_li = 0  # depth of open <li>
        self.quote = 0  # depth of open <blockquote>
        self.just_opened = False  # a bullet or "> " was just written: the next block continues it

    def _nl(self, n: int) -> None:
        text = "".join(self.out)
        have = len(text) - len(text.rstrip("\n"))
        if text and have < n:
            self.out.append("\n" * (n - have))

    def _link(self, kind: str, ref: str) -> str:
        label = self.resolve(kind, ref) if self.resolve else None
        if label is None:
            return f"[[missing {kind} link]]"
        return f"[[{label}]]"

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "blockquote":
            self._nl(2)
            self.out.append("> ")
            self.quote += 1
            self.just_opened = True
        elif tag in _BLOCKS:
            if not self.just_opened:
                self._nl(1 if self.in_li else 2)
                if self.quote:
                    self.out.append("> ")
            if tag.startswith("h") and len(tag) == 2:
                self.out.append("#" * max(int(tag[1]), 3) + " ")  # h3/h4 sit under the "## section" level
        elif tag == "br":
            self.out.append("\n")
        elif tag in ("strong", "b", "em", "i"):
            self.marks.append(len(self.out))
            self.out.append("**" if tag in ("strong", "b") else "*")
        elif tag == "hr":
            self._nl(2)
            self.out.append("---")
            self._nl(2)
        elif tag in ("ul", "ol"):
            self._nl(1)
            self.lists.append([tag, 0])
        elif tag == "li":
            self._nl(1)
            depth = max(len(self.lists) - 1, 0)
            if self.lists and self.lists[-1][0] == "ol":
                self.lists[-1][1] += 1
                bullet = f"{self.lists[-1][1]}. "
            else:
                bullet = "- "
            self.out.append("  " * depth + bullet)
            self.in_li += 1
            self.just_opened = True
        elif tag == "a":
            self.href = a.get("href")
            self.link_text_start = len("".join(self.out))
        elif tag == "tag-component":
            kind, _, ref = (a.get("id") or "").partition("/")
            self.out.append(self._link(kind, ref))
        elif tag in ("destiny-component", "intrigue-component"):
            ref = a.get("idhash") or a.get("id") or ""
            self.out.append(self._link("arcane", ref))

    def handle_endtag(self, tag):
        if tag == "blockquote":
            self.quote = max(self.quote - 1, 0)
            self._nl(2)
        elif tag == "li":
            self.in_li = max(self.in_li - 1, 0)
            self.just_opened = False
        elif tag in _BLOCKS:
            if not self.in_li:
                self._nl(2)
        elif tag in ("strong", "b", "em", "i"):
            self._close_mark("**" if tag in ("strong", "b") else "*")
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self._nl(2 if not self.lists else 1)
        elif tag == "a":
            text = "".join(self.out)[self.link_text_start:].strip()
            if self.href and self.href not in text:
                self.out.append(f" ({self.href})")
            self.href = None

    def _close_mark(self, marker: str) -> None:
        if not self.marks:
            return
        start = self.marks.pop()
        inner = "".join(self.out[start + 1:])
        if not inner.strip():  # empty emphasis: drop the opening marker
            del self.out[start]
            return
        # keep markers tight against the text: "**word** " not "**word **"
        stripped = inner.rstrip()
        self.out[start + 1:] = [stripped, marker, inner[len(stripped):]]

    def handle_data(self, data):
        if data.strip():
            self.just_opened = False
        self.out.append(data)


def _tidy(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"(?<=\S)[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_text(html: str | None, resolve: Resolver | None = None) -> str:
    if not html:
        return ""
    conv = _Converter(resolve)
    conv.feed(html)
    conv.close()
    return _tidy("".join(conv.out))


def normalize(s: str) -> str:
    """Case- and accent-insensitive form used for matching."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().casefold()
