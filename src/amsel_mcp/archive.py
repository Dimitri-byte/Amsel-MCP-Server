"""Reading Amsel Suite save files.

A ``.tome`` or ``.lore`` file is a plain tar archive containing ``data.json``
(the whole project, minified JSON) and an ``img/`` folder. A ``.lorekit`` is the
same kind of archive holding only Lore templates (no pages), to be imported into a Lore.
"""

from __future__ import annotations

import json
import tarfile
import threading
from pathlib import Path
from typing import Any

SUFFIXES = {".tome": "tome", ".lore": "lore", ".lorekit": "lorekit"}

_cache: dict[Path, tuple[tuple[int, int], Any]] = {}
_lock = threading.Lock()


class AmselFileError(ValueError):
    """Raised when a file is not a readable Amsel archive."""


def kind_of(path: Path) -> str | None:
    return SUFFIXES.get(path.suffix.lower())


def read_data_json(path: Path) -> dict:
    """Return the parsed ``data.json`` of an Amsel archive (no image extraction)."""
    try:
        with tarfile.open(path, "r") as tf:
            for member in tf:
                if member.isfile() and member.name.lstrip("./") == "data.json":
                    fh = tf.extractfile(member)
                    if fh is None:
                        break
                    return json.load(fh)
    except (tarfile.TarError, OSError, json.JSONDecodeError) as exc:
        raise AmselFileError(f"Cannot read {path}: {exc}") from exc
    raise AmselFileError(f"{path} has no data.json")


def load_cached(path: Path, factory):
    """Build ``factory(path, data)`` once per file version (mtime + size)."""
    path = path.resolve()
    st = path.stat()
    stamp = (st.st_mtime_ns, st.st_size)
    with _lock:
        hit = _cache.get(path)
        if hit and hit[0] == stamp:
            return hit[1]
    obj = factory(path, read_data_json(path))
    with _lock:
        _cache[path] = (stamp, obj)
    return obj
