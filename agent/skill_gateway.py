"""Skill Gateway — bidirectional skill sync with filesystem watcher.

Makes Hermes skills (under ~/.hermes/skills/) visible to Claude Code's
native Skill tool by creating symlinks in ~/.agents/skills/ and
~/.claude/skills/. Also syncs Claude-side skills back to Hermes.

Runs a background fswatch/watchdog thread that detects skill additions
and deletions on either side and reconciles in real time.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

HERMES_SKILLS_DIR = Path.home() / ".hermes" / "skills"
AGENTS_SKILLS_DIR = Path.home() / ".agents" / "skills"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
COLLISION_LOG = Path.home() / ".hermes" / "sync" / "skill_collisions.log"


class SkillGateway:
    """Bidirectional skill reconciliation with optional live watcher."""

    def __init__(self):
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def reconcile(self) -> None:
        """Full bidirectional reconcile: Hermes→Claude and Claude→Hermes.

        Also cleans up dangling symlinks on both sides.
        """
        self._reconcile_hermes_to_claude()
        self._reconcile_claude_to_hermes()
        self._cleanup_dangling()

    def start_watcher(self) -> None:
        """Start a background thread that watches for skill changes."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return

        self._stop_event.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop,
            name="skill-gateway-watcher",
            daemon=True,
        )
        self._watcher_thread.start()
        logger.info("skill_gateway: watcher started")

    def stop_watcher(self) -> None:
        """Stop the background watcher thread."""
        self._stop_event.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2)
            self._watcher_thread = None
            logger.info("skill_gateway: watcher stopped")

    def _reconcile_hermes_to_claude(self) -> None:
        """Sync Hermes skills → ~/.agents/skills/ → ~/.claude/skills/."""
        if not HERMES_SKILLS_DIR.is_dir():
            logger.debug("skill_gateway: %s not found, skipping", HERMES_SKILLS_DIR)
            return

        AGENTS_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        for skill_md in HERMES_SKILLS_DIR.rglob("SKILL.md"):
            skill_dir = skill_md.parent
            name = skill_dir.name
            agents_link = AGENTS_SKILLS_DIR / name
            claude_link = CLAUDE_SKILLS_DIR / name

            if agents_link.exists() or agents_link.is_symlink():
                if agents_link.is_symlink():
                    if agents_link.resolve() == skill_dir.resolve():
                        self._ensure_claude_link(claude_link, agents_link)
                        continue
                self._log_collision(name, skill_dir, agents_link)
                continue

            agents_link.symlink_to(skill_dir)
            logger.info("skill_gateway: hermes→agents %s -> %s", agents_link, skill_dir)
            self._ensure_claude_link(claude_link, agents_link)

    def _reconcile_claude_to_hermes(self) -> None:
        """Sync Claude-native skills back to Hermes visibility.

        If ~/.agents/skills/<name> exists and is NOT a symlink to a Hermes
        skill, register it in ~/.hermes/skills/_claude/<name> as a symlink
        so Hermes' skill_view/skills_list can see it.
        """
        if not AGENTS_SKILLS_DIR.is_dir():
            return

        hermes_claude_bridge = HERMES_SKILLS_DIR / "_claude"

        for entry in AGENTS_SKILLS_DIR.iterdir():
            name = entry.name
            if not entry.is_dir():
                continue

            # Skip if this is already a Hermes-originated symlink
            if entry.is_symlink():
                target = entry.resolve()
                try:
                    target.relative_to(HERMES_SKILLS_DIR.resolve())
                    continue  # Points into Hermes skills — skip
                except ValueError:
                    pass  # Points elsewhere — this is a Claude-native skill

            # Check if we already have a bridge symlink
            bridge_link = hermes_claude_bridge / name
            if bridge_link.exists() or bridge_link.is_symlink():
                continue

            # Create bridge: ~/.hermes/skills/_claude/<name> → ~/.agents/skills/<name>
            try:
                hermes_claude_bridge.mkdir(parents=True, exist_ok=True)
                bridge_link.symlink_to(entry.resolve())
                logger.info("skill_gateway: claude→hermes %s -> %s", bridge_link, entry)
            except OSError as exc:
                logger.debug("skill_gateway: failed to bridge %s: %s", name, exc)

    def _cleanup_dangling(self) -> None:
        """Remove symlinks whose targets no longer exist."""
        for dir_path in [AGENTS_SKILLS_DIR, CLAUDE_SKILLS_DIR]:
            if not dir_path.is_dir():
                continue
            for entry in dir_path.iterdir():
                if entry.is_symlink() and not entry.resolve().exists():
                    logger.info("skill_gateway: removing dangling symlink %s", entry)
                    try:
                        entry.unlink()
                    except OSError as exc:
                        logger.debug("skill_gateway: failed to unlink %s: %s", entry, exc)

        # Also clean up Hermes-side _claude bridges that are dangling
        bridge_dir = HERMES_SKILLS_DIR / "_claude"
        if bridge_dir.is_dir():
            for entry in bridge_dir.iterdir():
                if entry.is_symlink() and not entry.resolve().exists():
                    logger.info("skill_gateway: removing dangling bridge %s", entry)
                    try:
                        entry.unlink()
                    except OSError as exc:
                        logger.debug("skill_gateway: failed to unlink %s: %s", entry, exc)

    def _watch_loop(self) -> None:
        """Background thread: poll for changes every 2 seconds.

        Uses polling rather than platform-specific watchers (fsevents/inotify)
        to avoid a hard dependency on watchdog. The 2s interval is fine for
        skill changes which are infrequent.
        """
        logger.debug("skill_gateway: watcher loop starting")
        while not self._stop_event.is_set():
            try:
                self.reconcile()
            except Exception:
                logger.debug("skill_gateway: watcher reconcile error", exc_info=True)
            self._stop_event.wait(timeout=2.0)

    def _ensure_claude_link(self, claude_link: Path, agents_link: Path) -> None:
        """Create ~/.claude/skills/<name> -> ~/.agents/skills/<name> if missing."""
        if claude_link.exists() or claude_link.is_symlink():
            return
        claude_link.symlink_to(agents_link)
        logger.info("skill_gateway: linked %s -> %s", claude_link, agents_link)

    def _log_collision(self, name: str, hermes_path: Path, existing_path: Path) -> None:
        """Log a skill name collision without overwriting."""
        logger.warning(
            "skill_gateway: collision for '%s' — existing %s wins over Hermes %s",
            name, existing_path, hermes_path,
        )
        try:
            COLLISION_LOG.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat()
            line = f"{ts} | name={name} | hermes={hermes_path} | existing={existing_path}\n"
            with open(COLLISION_LOG, "a") as f:
                f.write(line)
        except OSError as exc:
            logger.debug("skill_gateway: failed to write collision log: %s", exc)
