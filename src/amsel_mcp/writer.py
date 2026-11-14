"""Safely writing Amsel archives back to disk.

Every save:
1. refuses if the Amsel app that edits this kind of file (Tome or Lore) is running,
   because it would overwrite our change (or we would overwrite its unsaved work);
2. refuses if the file changed on disk since it was read;
3. copies the current file to ``.amsel-backups/`` next to it;
4. rebuilds the tar with the new ``data.json``, every other member unchanged and any
   new files (images) appended, in a temporary file that is re-read and checked
   before replacing the original.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import socket
import tarfile
import tempfile
import threading
import time
from pathlib import Path

from .archive import kind_of, read_data_json

BACKUP_DIR = ".amsel-backups"
KEEP_BACKUPS = 20
_write_lock = threading.Lock()


class WriteRefused(ValueError):
    """The write was not attempted; nothing changed on disk."""


def file_stamp(path: Path) -> tuple[int, int]:
    st = path.stat()
    return (st.st_mtime_ns, st.st_size)


def dump_json(data: dict) -> bytes:
    """Serialize like Amsel does (compact, UTF-8): an unchanged file round-trips byte for byte."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# --- is the app open? --------------------------------------------------------

def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def app_running(kind: str) -> bool:
    """True when the Tome/Lore desktop app holds its Chromium singleton lock on this machine."""
    lock = _config_home() / kind / "SingletonLock"
    try:
        target = os.readlink(lock)  # "<hostname>-<pid>"
    except OSError:
        return False
    host, _, pid = target.rpartition("-")
    if host and host != socket.gethostname():
        return False
    try:
        os.kill(int(pid), 0)
    except (ValueError, ProcessLookupError):
        return False  # stale lock left by a crash
    except PermissionError:
        return True
    return True


def ensure_app_closed(path: Path) -> None:
    if os.environ.get("AMSEL_SKIP_APP_CHECK") == "1":
        return
    kind = kind_of(path)
    if kind and app_running(kind):
        app = "Tome" if kind == "tome" else "Lore"
        raise WriteRefused(
            f"{app} is open: close the {app} application before writing to {path.name}, "
            f"otherwise it would overwrite the change (or lose its own unsaved work). Nothing was written."
        )


# --- backups -----------------------------------------------------------------

def backup(path: Path) -> Path:
    bdir = path.parent / BACKUP_DIR
    bdir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = bdir / f"{path.stem}.{stamp}{path.suffix}"
    n = 1
    while dest.exists():
        dest = bdir / f"{path.stem}.{stamp}-{n}{path.suffix}"
        n += 1
    shutil.copy2(path, dest)
    olds = sorted(bdir.glob(f"{path.stem}.*{path.suffix}"), key=lambda p: p.stat().st_mtime)
    for old in olds[:-KEEP_BACKUPS]:
        old.unlink(missing_ok=True)
    return dest


# --- save --------------------------------------------------------------------

def save(path: Path, data: dict, expected_stamp: tuple[int, int],
         add_files: dict[str, bytes] | None = None) -> Path:
    """Write ``data`` as the new data.json of ``path``, plus ``add_files`` ({"img/x.png": bytes}).

    Returns the backup path.
    """
    add_files = dict(add_files or {})
    with _write_lock:
        ensure_app_closed(path)
        if file_stamp(path) != expected_stamp:
            raise WriteRefused(f"{path.name} changed on disk while preparing the edit. Nothing was written; retry.")
        raw = dump_json(data)
        bak = backup(path)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            with tarfile.open(path, "r") as src, tarfile.open(tmp, "w", format=tarfile.PAX_FORMAT) as dst:
                wrote_json = False
                template = None
                dirs = set()
                for m in src.getmembers():
                    name = m.name.lstrip("./").rstrip("/")
                    if name in add_files:
                        raise WriteRefused(f"{path.name} already contains {name}; nothing was written.")
                    if m.isdir():
                        dirs.add(name)
                    if m.isfile() and name == "data.json":
                        template = m
                        info = tarfile.TarInfo(m.name)
                        for attr in ("mode", "uid", "gid", "uname", "gname"):
                            setattr(info, attr, getattr(m, attr))
                        info.size = len(raw)
                        info.mtime = int(time.time())
                        dst.addfile(info, io.BytesIO(raw))
                        wrote_json = True
                    elif m.isfile():
                        dst.addfile(m, src.extractfile(m))
                    else:
                        dst.addfile(m)
                if not wrote_json:
                    raise WriteRefused(f"{path.name} has no data.json; nothing was written.")
                for name, blob in add_files.items():
                    parent = name.rpartition("/")[0]
                    if parent and parent not in dirs:
                        d = tarfile.TarInfo(parent)
                        d.type = tarfile.DIRTYPE
                        for attr in ("uid", "gid", "uname", "gname"):
                            setattr(d, attr, getattr(template, attr))
                        d.mode = 0o775
                        d.mtime = int(time.time())
                        dst.addfile(d)
                        dirs.add(parent)
                    info = tarfile.TarInfo(name)
                    for attr in ("mode", "uid", "gid", "uname", "gname"):
                        setattr(info, attr, getattr(template, attr))
                    info.size = len(blob)
                    info.mtime = int(time.time())
                    dst.addfile(info, io.BytesIO(blob))
            if read_data_json(tmp) != data:
                raise WriteRefused("Verification of the rewritten file failed; nothing was written.")
            if add_files:
                with tarfile.open(tmp, "r") as chk:
                    sizes = {m.name.lstrip("./"): m.size for m in chk.getmembers() if m.isfile()}
                if any(sizes.get(n) != len(b) for n, b in add_files.items()):
                    raise WriteRefused("Verification of the added files failed; nothing was written.")
            shutil.copymode(path, tmp)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return bak

