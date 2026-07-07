"""Bidirectional memory sync between Hermes and ~/.claude/CLAUDE.md.

Hermes manages a DELIMITED SECTION within CLAUDE.md — user's existing
content outside that section is never touched.

Section format inside CLAUDE.md:
    <!--hermes:memory:begin-->
    <USER.md content>
    <!--hermes:memory:separator-->
    <MEMORY.md content>
    <!--hermes:memory:end-->

Everything outside the markers belongs to the user and is preserved.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".hermes" / "memories"
USER_MD_PATH = MEMORY_DIR / "USER.md"
MEMORY_MD_PATH = MEMORY_DIR / "MEMORY.md"
CLAUDE_MD_PATH = Path.home() / ".claude" / "CLAUDE.md"

_BEGIN = "<!--hermes:memory:begin-->"
_SEP = "<!--hermes:memory:separator-->"
_END = "<!--hermes:memory:end-->"


def sync_hermes_to_claude() -> bool:
    """Push Hermes USER.md + MEMORY.md into the managed section of CLAUDE.md.

    Preserves any user content outside the markers.
    Returns True if the file was modified.
    """
    user_content = _read_file(USER_MD_PATH)
    memory_content = _read_file(MEMORY_MD_PATH)

    # Build the managed section
    if not user_content and not memory_content:
        # Remove section from CLAUDE.md if it exists
        return _remove_section()

    section = f"{_BEGIN}\n{user_content}\n{_SEP}\n{memory_content}\n{_END}"
    return _upsert_section(section)


def sync_claude_to_hermes() -> bool:
    """Pull the managed section from CLAUDE.md back to Hermes files.

    Returns True if any Hermes file was updated.
    """
    claude_content = _read_file(CLAUDE_MD_PATH)
    if not claude_content:
        return False

    if _BEGIN not in claude_content or _END not in claude_content:
        return False

    # Extract section content
    try:
        after_begin = claude_content.split(_BEGIN, 1)[1]
        section_content = after_begin.split(_END, 1)[0]
    except (IndexError, ValueError):
        return False

    if _SEP in section_content:
        user_part, memory_part = section_content.split(_SEP, 1)
    else:
        user_part = section_content
        memory_part = ""

    user_part = user_part.strip()
    memory_part = memory_part.strip()

    changed = False
    if user_part:
        changed |= _write_if_changed(USER_MD_PATH, user_part + "\n")
    if memory_part:
        changed |= _write_if_changed(MEMORY_MD_PATH, memory_part + "\n")

    return changed


class MemoryWatcher:
    """Watches both sides for changes and syncs bidirectionally."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_hermes_mtime: float = 0
        self._last_claude_mtime: float = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._snapshot_mtimes()
        self._thread = threading.Thread(
            target=self._loop, name="memory-watcher", daemon=True
        )
        self._thread.start()
        logger.info("memory_watcher: started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._check()
            except Exception:
                logger.debug("memory_watcher: check error", exc_info=True)
            self._stop.wait(timeout=2.0)

    def _check(self) -> None:
        hermes_mt = self._hermes_mtime()
        claude_mt = self._claude_mtime()

        if hermes_mt > self._last_hermes_mtime:
            sync_hermes_to_claude()
            self._snapshot_mtimes()
        elif claude_mt > self._last_claude_mtime:
            sync_claude_to_hermes()
            self._snapshot_mtimes()

    def _snapshot_mtimes(self) -> None:
        """Snapshot both sides after any sync to prevent echo loops."""
        self._last_hermes_mtime = self._hermes_mtime()
        self._last_claude_mtime = self._claude_mtime()

    def _hermes_mtime(self) -> float:
        mt = 0.0
        for p in (USER_MD_PATH, MEMORY_MD_PATH):
            try:
                mt = max(mt, p.stat().st_mtime)
            except OSError:
                pass
        return mt

    def _claude_mtime(self) -> float:
        try:
            return CLAUDE_MD_PATH.stat().st_mtime
        except OSError:
            return 0.0


# Backward compat aliases
sync_to_claude_md = sync_hermes_to_claude


def build_memory_append(max_bytes: int = 4096) -> str:
    """Build memory as a string (for non-file use cases like tests)."""
    user_content = _read_file(USER_MD_PATH)
    memory_content = _read_file(MEMORY_MD_PATH)
    if not user_content and not memory_content:
        return ""
    parts = [p for p in (user_content, memory_content) if p]
    result = "\n§\n".join(parts)
    if len(result.encode("utf-8")) > max_bytes:
        result = result.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return result


# ── Internal helpers ──────────────────────────────────────────────────────


def _upsert_section(section: str) -> bool:
    """Insert or replace the managed section in CLAUDE.md."""
    existing = _read_file(CLAUDE_MD_PATH)

    if _BEGIN in existing and _END in existing:
        # Replace existing section
        before = existing.split(_BEGIN, 1)[0]
        after_end = existing.split(_END, 1)[1] if _END in existing else ""
        new_content = before.rstrip("\n") + "\n" + section + "\n" + after_end.lstrip("\n")
    elif existing:
        # Append section to existing content
        new_content = existing.rstrip("\n") + "\n\n" + section + "\n"
    else:
        # File doesn't exist — section IS the content
        new_content = section + "\n"

    return _write_if_changed(CLAUDE_MD_PATH, new_content)


def _remove_section() -> bool:
    """Remove the managed section from CLAUDE.md, keep user content."""
    existing = _read_file(CLAUDE_MD_PATH)
    if not existing or _BEGIN not in existing:
        return False

    before = existing.split(_BEGIN, 1)[0]
    after_end = existing.split(_END, 1)[1] if _END in existing else ""
    new_content = (before.rstrip("\n") + "\n" + after_end.lstrip("\n")).strip()

    if not new_content:
        # Nothing left — remove the file
        try:
            CLAUDE_MD_PATH.unlink()
            return True
        except OSError:
            return False

    return _write_if_changed(CLAUDE_MD_PATH, new_content + "\n")


def _read_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_if_changed(path: Path, content: str) -> bool:
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == content:
                return False
        except OSError:
            pass

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError as exc:
        logger.warning("memory_sync: failed to write %s: %s", path, exc)
        return False
