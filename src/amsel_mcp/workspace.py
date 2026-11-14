"""Finding Amsel files on disk and opening them."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .archive import kind_of, load_cached
from .model import Lore, Tome
from .text import normalize

DEFAULT_ROOTS = ["~/Documents"]


def roots_from_env() -> list[Path]:
    raw = os.environ.get("AMSEL_PATHS", "")
    parts = [p for p in raw.split(os.pathsep) if p.strip()] or DEFAULT_ROOTS
    return [Path(p).expanduser() for p in parts]


class Workspace:
    def __init__(self, roots: list[Path] | None = None, ttl: float = 10.0):
        self.roots = roots if roots is not None else roots_from_env()
        self.ttl = ttl
        self._found: list[Path] = []
        self._found_at = 0.0

    # discovery -----------------------------------------------------------
    def discover(self) -> list[Path]:
        if time.monotonic() - self._found_at < self.ttl:
            return self._found
        found: list[Path] = []
        for root in self.roots:
            if root.is_file() and kind_of(root):
                found.append(root.resolve())
                continue
            if not root.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                for f in filenames:
                    p = Path(dirpath, f)
                    if kind_of(p):
                        found.append(p.resolve())
        self._found = sorted(set(found))
        self._found_at = time.monotonic()
        return self._found

    def resolve_path(self, ref: str, kind: str | tuple[str, ...] | None = None) -> Path:
        """Accept a path, a file name or a partial file name, of the given kind(s)."""
        kinds = (kind,) if isinstance(kind, str) else kind

        def ok(c: Path) -> bool:
            return bool(kind_of(c)) and (kinds is None or kind_of(c) in kinds)

        p = Path(ref).expanduser()
        if p.is_file() and ok(p):
            return p.resolve()
        cands = [c for c in self.discover() if ok(c)]
        key = normalize(Path(ref).stem if kind_of(Path(ref)) else ref)
        exact = [c for c in cands if normalize(c.stem) == key]
        hits = exact or [c for c in cands if key in normalize(c.stem)]
        what = "/".join(f".{k}" for k in kinds) if kinds else "Amsel"
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise ValueError(
                f"No {what} file matches {ref!r}. Known files: "
                + (", ".join(c.name for c in cands) or f"none (searched {', '.join(map(str, self.roots))})")
            )
        raise ValueError(f"Several {what} files match {ref!r}: " + ", ".join(str(c) for c in hits))

    # opening -------------------------------------------------------------
    def open(self, ref: str, kind: str | tuple[str, ...] | None = None) -> Tome | Lore:
        path = self.resolve_path(ref, kind)
        return load_cached(path, Tome if kind_of(path) == "tome" else Lore)

    def tome(self, ref: str) -> Tome:
        return self.open(ref, "tome")  # type: ignore[return-value]

    def lore(self, ref: str, kits: bool = True) -> Lore:
        """Open a .lore (or, when ``kits``, a .lorekit: same model, templates only)."""
        return self.open(ref, ("lore", "lorekit") if kits else "lore")  # type: ignore[return-value]

    def linked_lore(self, tome: Tome) -> Lore | None:
        """Find the Lore a Tome is linked to.

        Prefers a .lore next to the Tome with the same name as the recorded link
        (so copies are read together), then the recorded path itself, then any
        known .lore with that name.
        """
        linked = tome.data.get("linkedLorePath") or ""
        if not linked:
            return None
        stem = normalize(Path(linked.replace("\\", "/")).stem)
        siblings = [p for p in tome.path.parent.iterdir() if kind_of(p) == "lore"]
        candidates = [p for p in siblings if normalize(p.stem) == stem]
        if not candidates:
            candidates = [p for p in siblings if stem and stem in normalize(p.stem)]
        if not candidates and Path(linked).is_file():
            candidates = [Path(linked)]
        if not candidates:
            candidates = [p for p in self.discover() if kind_of(p) == "lore" and normalize(p.stem) == stem]
        if not candidates:
            return None
        return load_cached(candidates[0], Lore)
