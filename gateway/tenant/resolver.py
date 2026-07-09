"""Tenant resolver — maps IM identities to users and profiles."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gateway.tenant.models import User
    from gateway.tenant.registry import UserRegistry

logger = logging.getLogger(__name__)


class TenantResolver:
    """Resolves IM identities to users and Hermes profiles.

    Handles DM-only gating (group messages are skipped), user lookup
    via the registry, and optional auto-registration of unknown identities.
    """

    def __init__(self, registry: "UserRegistry", config: dict, provisioner=None):
        self._registry = registry
        self._config = config
        self._provisioner = provisioner

    @property
    def auto_register_enabled(self) -> bool:
        return self._config.get("auto_register", False)

    async def resolve_user(self, platform: str, platform_user_id: str) -> "User | None":
        """Look up a user by their IM identity.

        Returns the User if found, None otherwise.
        """
        return await self._registry.resolve_by_im_identity(platform, platform_user_id)

    async def auto_register_user(
        self,
        platform: str,
        platform_user_id: str,
        platform_metadata: dict | None = None,
    ) -> "User":
        """Create a new user, link IM identity, and provision a profile.

        Steps:
          1. Generate a username from the platform identity.
          2. Create the user record.
          3. Link the IM identity to the new user.
          4. Provision and map a Hermes profile for the user.

        Returns the newly created User.
        """
        username = self._registry.generate_username(platform, platform_user_id)
        display_name = None
        if platform_metadata:
            display_name = platform_metadata.get("display_name") or platform_metadata.get("name")

        logger.info(
            "Auto-registering user: platform=%s, platform_user_id=%s, username=%s",
            platform,
            platform_user_id,
            username,
        )

        user = await self._registry.create_user(
            username=username,
            display_name=display_name,
        )

        await self._registry.link_identity(
            user_id=user.id,
            platform=platform,
            platform_user_id=platform_user_id,
            metadata=platform_metadata,
        )

        # Allocate a container UID for the new user
        uid = await self._registry.allocate_container_uid(user.id)
        user.container_uid = uid

        # Provision a Hermes profile for the new user.
        if self._provisioner:
            profile_name = await self._provisioner.provision_profile(user)
        else:
            profile_name = username
            await self._registry.map_profile(
                user_id=user.id,
                profile_name=profile_name,
                is_primary=True,
            )

        logger.info(
            "Auto-registration complete: user_id=%s, profile=%s",
            user.id,
            profile_name,
        )
        return user

    async def get_profile_for_user(self, user: "User") -> str | None:
        """Get the primary profile name for a user."""
        return await self._registry.get_user_profile(user.id)

    async def resolve_or_register(
        self,
        platform: str,
        platform_user_id: str,
        chat_type: str,
        platform_metadata: dict | None = None,
    ) -> tuple["User | None", str | None, str | None]:
        """Main entry point: resolve an IM identity to a user and profile.

        Args:
            platform: The messaging platform (e.g. "telegram", "feishu").
            platform_user_id: The user's ID on that platform.
            chat_type: The chat type (e.g. "dm", "private", "group", "channel").
            platform_metadata: Optional metadata from the platform (display name, etc.).

        Returns:
            A tuple of (user, profile_name, rejection_message):
            - On success: (User, profile_name, None)
            - DM-only gating (group message): (None, None, None) — skip silently
            - Unknown user, auto-register disabled: (None, None, rejection_message)
        """
        # DM-only gating: skip group/channel messages entirely.
        if chat_type not in ("dm", "private"):
            logger.debug(
                "Skipping non-DM message: platform=%s, chat_type=%s",
                platform,
                chat_type,
            )
            return None, None, None

        # Attempt to resolve existing user.
        user = await self.resolve_user(platform, platform_user_id)

        if user is not None:
            profile_name = await self.get_profile_for_user(user)
            if profile_name is None:
                logger.warning(
                    "User %s (%s) has no primary profile mapped",
                    user.username,
                    user.id,
                )
            return user, profile_name, None

        # Unknown user — check auto-registration policy.
        if not self.auto_register_enabled:
            logger.info(
                "Rejecting unknown identity: platform=%s, platform_user_id=%s "
                "(auto_register disabled)",
                platform,
                platform_user_id,
            )
            return (
                None,
                None,
                "You are not registered. Please contact an administrator to gain access.",
            )

        # Auto-register the new user.
        user = await self.auto_register_user(
            platform=platform,
            platform_user_id=platform_user_id,
            platform_metadata=platform_metadata,
        )
        profile_name = await self.get_profile_for_user(user)
        return user, profile_name, None
