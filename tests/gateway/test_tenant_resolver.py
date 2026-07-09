"""Tests for gateway.tenant.resolver — TenantResolver identity resolution."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    reg.resolve_by_im_identity = AsyncMock(return_value=None)
    reg.get_user_profile = AsyncMock(return_value=None)
    reg.create_user = AsyncMock()
    reg.link_identity = AsyncMock()
    reg.map_profile = AsyncMock()
    reg.generate_username = MagicMock(return_value="telegram_12345")
    return reg


@pytest.fixture
def mock_provisioner():
    prov = MagicMock()
    prov.provision_profile = AsyncMock(return_value="telegram_12345")
    return prov


@pytest.fixture
def resolver(mock_registry, mock_provisioner):
    from gateway.tenant.resolver import TenantResolver

    config = {"auto_register": True, "profile_template": None}
    return TenantResolver(mock_registry, config, provisioner=mock_provisioner)


@pytest.fixture
def resolver_no_auto(mock_registry, mock_provisioner):
    from gateway.tenant.resolver import TenantResolver

    config = {"auto_register": False, "profile_template": None}
    return TenantResolver(mock_registry, config, provisioner=mock_provisioner)


class TestResolveOrRegister:
    @pytest.mark.asyncio
    async def test_skip_group_messages(self, resolver):
        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "12345", "group"
        )
        assert user is None
        assert profile is None
        assert reject is None

    @pytest.mark.asyncio
    async def test_skip_channel_messages(self, resolver):
        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "12345", "channel"
        )
        assert user is None
        assert profile is None
        assert reject is None

    @pytest.mark.asyncio
    async def test_known_user_resolved(self, resolver, mock_registry):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.username = "alice"
        mock_registry.resolve_by_im_identity.return_value = mock_user
        mock_registry.get_user_profile.return_value = "alice"

        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "12345", "dm"
        )
        assert user is mock_user
        assert profile == "alice"
        assert reject is None

    @pytest.mark.asyncio
    async def test_unknown_user_auto_register(self, resolver, mock_registry, mock_provisioner):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.username = "telegram_12345"
        mock_registry.resolve_by_im_identity.return_value = None
        mock_registry.create_user.return_value = mock_user
        mock_registry.get_user_profile.return_value = "telegram_12345"

        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "12345", "private", {"display_name": "Alice"}
        )
        assert user is mock_user
        assert profile == "telegram_12345"
        assert reject is None
        mock_provisioner.provision_profile.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_user_rejected_no_auto_register(self, resolver_no_auto, mock_registry):
        mock_registry.resolve_by_im_identity.return_value = None

        user, profile, reject = await resolver_no_auto.resolve_or_register(
            "telegram", "99999", "dm"
        )
        assert user is None
        assert profile is None
        assert "not registered" in reject.lower()

    @pytest.mark.asyncio
    async def test_dm_type_accepted(self, resolver, mock_registry):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_registry.resolve_by_im_identity.return_value = mock_user
        mock_registry.get_user_profile.return_value = "prof"

        user, profile, _ = await resolver.resolve_or_register(
            "feishu", "ou_abc", "dm"
        )
        assert user is mock_user

    @pytest.mark.asyncio
    async def test_private_type_accepted(self, resolver, mock_registry):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_registry.resolve_by_im_identity.return_value = mock_user
        mock_registry.get_user_profile.return_value = "prof"

        user, profile, _ = await resolver.resolve_or_register(
            "feishu", "ou_abc", "private"
        )
        assert user is mock_user


class TestResolveUser:
    @pytest.mark.asyncio
    async def test_resolve_existing(self, resolver, mock_registry):
        mock_user = MagicMock()
        mock_registry.resolve_by_im_identity.return_value = mock_user

        result = await resolver.resolve_user("telegram", "12345")
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_resolve_unknown(self, resolver, mock_registry):
        mock_registry.resolve_by_im_identity.return_value = None

        result = await resolver.resolve_user("slack", "U000")
        assert result is None
