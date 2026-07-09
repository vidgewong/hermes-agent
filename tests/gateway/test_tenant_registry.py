"""Tests for gateway.tenant.registry — UserRegistry CRUD operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.tenant.models import Base, IMIdentity, User, UserProfile
from gateway.tenant.registry import (
    DuplicateIdentityError,
    UserNotFoundError,
    UserRegistry,
    UserRegistryError,
)


@pytest.fixture
def registry(tmp_path):
    """Create a UserRegistry backed by an in-memory SQLite for testing."""
    pytest.importorskip("sqlalchemy")

    import asyncio

    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(setup())

    return UserRegistry(session_factory)


@pytest.fixture
def run(request):
    """Helper to run async tests."""
    import asyncio

    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    return _run


class TestCreateUser:
    def test_create_user_basic(self, registry, run):
        user = run(registry.create_user(username="alice", display_name="Alice"))
        assert user.username == "alice"
        assert user.display_name == "Alice"
        assert user.id is not None

    def test_create_user_duplicate_username(self, registry, run):
        run(registry.create_user(username="bob"))
        with pytest.raises(UserRegistryError, match="already exists"):
            run(registry.create_user(username="bob"))

    def test_create_user_all_fields(self, registry, run):
        user = run(
            registry.create_user(
                username="charlie",
                display_name="Charlie",
                email="charlie@test.com",
                wiw_id="W123",
                roles={"admin": True},
                responsibilities="Backend",
            )
        )
        assert user.email == "charlie@test.com"
        assert user.wiw_id == "W123"
        assert user.roles == {"admin": True}
        assert user.responsibilities == "Backend"


class TestGetUser:
    def test_get_user_exists(self, registry, run):
        created = run(registry.create_user(username="dave"))
        fetched = run(registry.get_user(created.id))
        assert fetched.username == "dave"

    def test_get_user_not_found(self, registry, run):
        with pytest.raises(UserNotFoundError):
            run(registry.get_user(uuid.uuid4()))

    def test_get_user_by_username(self, registry, run):
        run(registry.create_user(username="eve"))
        fetched = run(registry.get_user_by_username("eve"))
        assert fetched is not None
        assert fetched.username == "eve"

    def test_get_user_by_username_missing(self, registry, run):
        result = run(registry.get_user_by_username("nonexistent"))
        assert result is None


class TestUpdateUser:
    def test_update_user_fields(self, registry, run):
        user = run(registry.create_user(username="frank"))
        updated = run(registry.update_user(user.id, display_name="Frank Updated"))
        assert updated.display_name == "Frank Updated"

    def test_update_user_not_found(self, registry, run):
        with pytest.raises(UserNotFoundError):
            run(registry.update_user(uuid.uuid4(), display_name="X"))


class TestListUsers:
    def test_list_users_empty(self, registry, run):
        users = run(registry.list_users())
        assert users == []

    def test_list_users_returns_all(self, registry, run):
        run(registry.create_user(username="u1"))
        run(registry.create_user(username="u2"))
        users = run(registry.list_users())
        assert len(users) == 2


class TestIdentityLinking:
    def test_link_identity(self, registry, run):
        user = run(registry.create_user(username="grace"))
        identity = run(
            registry.link_identity(user.id, "telegram", "12345", {"name": "Grace"})
        )
        assert identity.platform == "telegram"
        assert identity.platform_user_id == "12345"

    def test_link_duplicate_identity(self, registry, run):
        user = run(registry.create_user(username="heidi"))
        run(registry.link_identity(user.id, "telegram", "99999"))
        with pytest.raises(DuplicateIdentityError):
            run(registry.link_identity(user.id, "telegram", "99999"))

    def test_link_identity_user_not_found(self, registry, run):
        with pytest.raises(UserNotFoundError):
            run(registry.link_identity(uuid.uuid4(), "telegram", "11111"))

    def test_resolve_by_im_identity(self, registry, run):
        user = run(registry.create_user(username="ivan"))
        run(registry.link_identity(user.id, "feishu", "ou_abc123"))
        resolved = run(registry.resolve_by_im_identity("feishu", "ou_abc123"))
        assert resolved is not None
        assert resolved.username == "ivan"

    def test_resolve_by_im_identity_unknown(self, registry, run):
        result = run(registry.resolve_by_im_identity("slack", "U000"))
        assert result is None

    def test_unlink_identity(self, registry, run):
        user = run(registry.create_user(username="judy"))
        identity = run(registry.link_identity(user.id, "discord", "D001"))
        run(registry.unlink_identity(identity.id))
        resolved = run(registry.resolve_by_im_identity("discord", "D001"))
        assert resolved is None


class TestProfileMapping:
    def test_map_profile(self, registry, run):
        user = run(registry.create_user(username="karl"))
        profile = run(registry.map_profile(user.id, "karl"))
        assert profile.profile_name == "karl"
        assert profile.is_primary is True

    def test_get_user_profile(self, registry, run):
        user = run(registry.create_user(username="lara"))
        run(registry.map_profile(user.id, "lara"))
        name = run(registry.get_user_profile(user.id))
        assert name == "lara"

    def test_get_user_profile_none(self, registry, run):
        user = run(registry.create_user(username="mike"))
        name = run(registry.get_user_profile(user.id))
        assert name is None

    def test_map_profile_duplicate(self, registry, run):
        user = run(registry.create_user(username="nora"))
        run(registry.map_profile(user.id, "nora"))
        with pytest.raises(UserRegistryError, match="already mapped"):
            run(registry.map_profile(user.id, "nora"))


class TestUsernameGeneration:
    def test_generate_from_telegram(self, registry):
        name = registry.generate_username("telegram", "123456")
        assert name == "telegram_123456"

    def test_generate_sanitizes_special_chars(self, registry):
        name = registry.generate_username("feishu", "ou_abc@def!xyz")
        assert name == "feishu_ou_abcdefxyz"

    def test_generate_truncates_long_id(self, registry):
        long_id = "a" * 100
        name = registry.generate_username("slack", long_id)
        assert len(name) <= len("slack_") + 32

    def test_generate_fallback_for_empty(self, registry):
        name = registry.generate_username("test", "!!!@@@")
        assert name.startswith("test_")
        assert len(name) > len("test_")
