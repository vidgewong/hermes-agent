"""User registry — CRUD operations for multi-tenant user management."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from gateway.tenant.models import IMIdentity, User, UserProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UserRegistryError(Exception):
    pass


class UserNotFoundError(UserRegistryError):
    pass


class DuplicateIdentityError(UserRegistryError):
    pass


class UserRegistry:
    """Manages user records, IM identity links, and profile mappings."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def _session(self) -> "AsyncSession":
        return self._session_factory()

    async def create_user(
        self,
        username: str,
        display_name: str | None = None,
        email: str | None = None,
        wiw_id: str | None = None,
        roles: dict | None = None,
        responsibilities: str | None = None,
    ) -> User:
        async with await self._session() as session:
            user = User(
                username=username,
                display_name=display_name,
                email=email,
                wiw_id=wiw_id,
                roles=roles or {},
                responsibilities=responsibilities,
            )
            session.add(user)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise UserRegistryError(f"Username '{username}' already exists")
            await session.refresh(user)
            return user

    async def get_user(self, user_id: uuid.UUID) -> User:
        async with await self._session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise UserNotFoundError(f"User {user_id} not found")
            return user

    async def get_user_by_username(self, username: str) -> User | None:
        async with await self._session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

    async def update_user(self, user_id: uuid.UUID, **kwargs) -> User:
        async with await self._session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise UserNotFoundError(f"User {user_id} not found")
            for key, value in kwargs.items():
                if hasattr(user, key) and key not in ("id", "created_at"):
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(user)
            return user

    async def list_users(self) -> list[User]:
        async with await self._session() as session:
            result = await session.execute(select(User).order_by(User.created_at))
            return list(result.scalars().all())

    async def link_identity(
        self,
        user_id: uuid.UUID,
        platform: str,
        platform_user_id: str,
        metadata: dict | None = None,
    ) -> IMIdentity:
        async with await self._session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise UserNotFoundError(f"User {user_id} not found")
            identity = IMIdentity(
                user_id=user_id,
                platform=platform,
                platform_user_id=platform_user_id,
                metadata_=metadata or {},
            )
            session.add(identity)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise DuplicateIdentityError(
                    f"Identity {platform}:{platform_user_id} already linked"
                )
            await session.refresh(identity)
            return identity

    async def unlink_identity(self, identity_id: uuid.UUID) -> None:
        async with await self._session() as session:
            identity = await session.get(IMIdentity, identity_id)
            if identity:
                await session.delete(identity)
                await session.commit()

    async def resolve_by_im_identity(
        self, platform: str, platform_user_id: str
    ) -> User | None:
        async with await self._session() as session:
            result = await session.execute(
                select(User)
                .join(IMIdentity)
                .where(
                    IMIdentity.platform == platform,
                    IMIdentity.platform_user_id == platform_user_id,
                )
            )
            return result.scalar_one_or_none()

    async def map_profile(
        self,
        user_id: uuid.UUID,
        profile_name: str,
        is_primary: bool = True,
    ) -> UserProfile:
        async with await self._session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise UserNotFoundError(f"User {user_id} not found")
            profile = UserProfile(
                user_id=user_id,
                profile_name=profile_name,
                is_primary=is_primary,
            )
            session.add(profile)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise UserRegistryError(
                    f"Profile '{profile_name}' already mapped for user {user_id}"
                )
            await session.refresh(profile)
            return profile

    async def get_user_profile(self, user_id: uuid.UUID) -> str | None:
        """Get the primary profile name for a user."""
        async with await self._session() as session:
            result = await session.execute(
                select(UserProfile)
                .where(UserProfile.user_id == user_id, UserProfile.is_primary.is_(True))
            )
            profile = result.scalar_one_or_none()
            return profile.profile_name if profile else None

    def generate_username(self, platform: str, platform_user_id: str) -> str:
        """Generate a username for auto-registration from IM identity."""
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", platform_user_id)[:32]
        if not sanitized:
            sanitized = uuid.uuid4().hex[:8]
        return f"{platform}_{sanitized}"

    async def allocate_container_uid(self, user_id: uuid.UUID) -> int:
        """Allocate and persist a unique container UID for a user.

        UIDs start at 2000 and increment based on total user count.
        """
        from gateway.tenant.shared_container import _UID_BASE

        async with await self._session() as session:
            user = await session.get(User, user_id)
            if user and user.container_uid is not None:
                return user.container_uid

            # Count existing users to determine next UID
            from sqlalchemy import func, select
            result = await session.execute(
                select(func.count()).select_from(User)
            )
            count = result.scalar() or 0
            uid = _UID_BASE + count

            if user:
                user.container_uid = uid
                await session.commit()
                await session.refresh(user)
            return uid
