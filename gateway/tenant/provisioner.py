"""Tenant profile provisioner — creates Hermes profiles for tenants."""

from __future__ import annotations

import asyncio
import logging
import re
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from hermes_cli.profiles import (
    create_profile,
    get_profile_dir,
    normalize_profile_name,
    profile_exists,
)

if TYPE_CHECKING:
    from gateway.tenant.models import User
    from gateway.tenant.registry import UserRegistry

logger = logging.getLogger(__name__)

# Characters allowed in profile names: lowercase alphanumeric, hyphens, underscores
_SAFE_PROFILE_RE = re.compile(r"[^a-z0-9_-]")


def _sanitize_profile_name(username: str) -> str:
    """Sanitize a username into a filesystem-safe profile name.

    Lowercases, replaces unsafe characters with underscores, strips leading
    underscores/hyphens, and truncates to 64 characters.
    """
    name = username.lower().strip()
    name = _SAFE_PROFILE_RE.sub("_", name)
    # Strip leading non-alphanumeric (profile names must start with [a-z0-9])
    name = name.lstrip("_-")
    # Truncate to 64 chars (profile name limit)
    name = name[:64]
    if not name:
        # Fallback for completely unsanitizable names
        import uuid as _uuid

        name = f"tenant_{_uuid.uuid4().hex[:8]}"
    return name


class TenantProvisioner:
    """Creates and manages Hermes profiles for multi-tenant users.

    Uses the existing profiles.py infrastructure to create isolated profile
    directories, then maps them in the UserRegistry.
    """

    def __init__(self, registry: "UserRegistry", config: dict):
        """
        Parameters
        ----------
        registry:
            UserRegistry instance for managing user-profile mappings.
        config:
            gateway.multi_tenant config dict. Recognized keys:
            - profile_template: default template profile to clone from
        """
        self._registry = registry
        self._config = config

    @property
    def _default_template(self) -> str | None:
        """The default profile template from config."""
        return self._config.get("profile_template")

    async def provision_profile(self, user: "User", template: str | None = None) -> str:
        """Create a profile for the user. Returns the profile name.

        Parameters
        ----------
        user:
            User model instance (must have .id and .username).
        template:
            Profile to clone from. Falls back to config.profile_template.
            If None/unset, creates a bare profile.

        Returns
        -------
        str
            The provisioned profile name.

        Notes
        -----
        Idempotent: if the profile already exists and is mapped to the user,
        returns the existing profile name without modification.
        """
        profile_name = _sanitize_profile_name(user.username)

        # Check if already provisioned
        existing = await self._registry.get_user_profile(user.id)
        if existing and profile_exists(existing):
            logger.debug(
                "User %s already provisioned with profile '%s'",
                user.username,
                existing,
            )
            return existing

        # Resolve template
        clone_from = template or self._default_template

        # Create the profile (sync call — run in executor)
        if not profile_exists(profile_name):
            loop = asyncio.get_running_loop()
            try:
                kwargs = {}
                if clone_from:
                    kwargs["clone_from"] = clone_from
                await loop.run_in_executor(
                    None,
                    partial(create_profile, profile_name, **kwargs),
                )
                logger.info(
                    "Created profile '%s' for user '%s' (template=%s)",
                    profile_name,
                    user.username,
                    clone_from or "none",
                )
            except FileExistsError:
                # Race condition: another coroutine created it concurrently
                logger.debug(
                    "Profile '%s' already exists on disk (race), continuing",
                    profile_name,
                )

        # Ensure workspace directory exists with correct ownership
        profile_dir = get_profile_dir(profile_name)
        workspace_dir = profile_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Set ownership to the user's container_uid so container writes work.
        # Uses the shared tenant container (which has CAP_CHOWN).
        uid = getattr(user, "container_uid", None)
        if uid:
            import subprocess
            _container = "hermes-tenant-shared"
            # Try the shared container first (lightweight), fall back to temp container
            result = subprocess.run(
                ["docker", "exec", _container,
                 "chown", "-R", f"{uid}:{uid}", f"/home/{user.username}/workspace"],
                capture_output=True, check=False,
            )
            if result.returncode != 0:
                # Container not running or path not mounted yet — use host chmod
                # (works if current process uid owns the dir)
                import os
                try:
                    os.chown(str(workspace_dir), uid, uid)
                except OSError:
                    logger.debug("Could not chown workspace to uid %d", uid)

        # Ensure .claude directory with a basic CLAUDE.md
        claude_dir = profile_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"
        if not claude_md.exists():
            claude_md.write_text(
                f"# Tenant Profile: {user.username}\n\n"
                f"This profile is managed by the multi-tenant provisioner.\n"
            )

        # Map profile in registry (if not already mapped)
        if not existing:
            try:
                await self._registry.map_profile(
                    user_id=user.id,
                    profile_name=profile_name,
                    is_primary=True,
                )
                logger.info(
                    "Mapped profile '%s' to user '%s' (id=%s)",
                    profile_name,
                    user.username,
                    user.id,
                )
            except Exception as exc:
                # Profile mapping may already exist from a previous partial run
                logger.warning(
                    "Could not map profile '%s' for user '%s': %s",
                    profile_name,
                    user.username,
                    exc,
                )

        return profile_name

    async def deprovision_profile(self, user: "User") -> None:
        """Remove the profile mapping for a user.

        Does NOT delete the profile directory on disk — data is preserved
        for potential recovery or audit.
        """
        existing = await self._registry.get_user_profile(user.id)
        if not existing:
            logger.debug(
                "User '%s' has no profile mapping to remove", user.username
            )
            return

        # Remove all profile mappings for this user
        from sqlalchemy import select

        from gateway.tenant.models import UserProfile

        async with await self._registry._session() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
            profiles = result.scalars().all()
            for profile in profiles:
                await session.delete(profile)
            await session.commit()

        logger.info(
            "Deprovisioned profile mapping for user '%s' (profile was '%s')",
            user.username,
            existing,
        )

    async def is_provisioned(self, user: "User") -> bool:
        """Check if a user has a provisioned profile.

        Returns True only if both a registry mapping exists AND the profile
        directory is present on disk.
        """
        existing = await self._registry.get_user_profile(user.id)
        if not existing:
            return False
        return profile_exists(existing)
