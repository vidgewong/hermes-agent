"""Tests for gateway.tenant.provisioner — TenantProvisioner profile lifecycle."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    reg.get_user_profile = AsyncMock(return_value=None)
    reg.map_profile = AsyncMock()
    reg._session = AsyncMock()
    return reg


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    return user


@pytest.fixture
def provisioner(mock_registry):
    from gateway.tenant.provisioner import TenantProvisioner

    config = {"profile_template": None, "container_idle_timeout": 3600}
    return TenantProvisioner(mock_registry, config)


class TestProvisionProfile:
    @pytest.mark.asyncio
    async def test_provision_new_profile(self, provisioner, mock_registry, mock_user, tmp_path):
        with patch("gateway.tenant.provisioner.profile_exists", return_value=False), \
             patch("gateway.tenant.provisioner.create_profile") as mock_create, \
             patch("gateway.tenant.provisioner.get_profile_dir", return_value=tmp_path):
            result = await provisioner.provision_profile(mock_user)
            assert result == "testuser"
            mock_create.assert_called_once()
            mock_registry.map_profile.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_provision_idempotent(self, provisioner, mock_registry, mock_user, tmp_path):
        mock_registry.get_user_profile.return_value = "testuser"
        with patch("gateway.tenant.provisioner.profile_exists", return_value=True), \
             patch("gateway.tenant.provisioner.get_profile_dir", return_value=tmp_path):
            result = await provisioner.provision_profile(mock_user)
            assert result == "testuser"
            mock_registry.map_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_provision_creates_workspace(self, provisioner, mock_registry, mock_user, tmp_path):
        with patch("gateway.tenant.provisioner.profile_exists", return_value=False), \
             patch("gateway.tenant.provisioner.create_profile"), \
             patch("gateway.tenant.provisioner.get_profile_dir", return_value=tmp_path):
            await provisioner.provision_profile(mock_user)
            assert (tmp_path / "workspace").exists()

    @pytest.mark.asyncio
    async def test_provision_creates_claude_md(self, provisioner, mock_registry, mock_user, tmp_path):
        with patch("gateway.tenant.provisioner.profile_exists", return_value=False), \
             patch("gateway.tenant.provisioner.create_profile"), \
             patch("gateway.tenant.provisioner.get_profile_dir", return_value=tmp_path):
            await provisioner.provision_profile(mock_user)
            assert (tmp_path / ".claude" / "CLAUDE.md").exists()

    @pytest.mark.asyncio
    async def test_provision_with_template(self, provisioner, mock_registry, mock_user, tmp_path):
        with patch("gateway.tenant.provisioner.profile_exists", return_value=False), \
             patch("gateway.tenant.provisioner.create_profile") as mock_create, \
             patch("gateway.tenant.provisioner.get_profile_dir", return_value=tmp_path):
            await provisioner.provision_profile(mock_user, template="base")
            mock_create.assert_called_once_with("testuser", clone_from="base")


class TestDeprovisionProfile:
    @pytest.mark.asyncio
    async def test_deprovision_removes_mapping(self, provisioner, mock_registry, mock_user):
        mock_registry.get_user_profile.return_value = "testuser"
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_registry._session.return_value = mock_session

        await provisioner.deprovision_profile(mock_user)

    @pytest.mark.asyncio
    async def test_deprovision_noop_if_not_mapped(self, provisioner, mock_registry, mock_user):
        mock_registry.get_user_profile.return_value = None
        await provisioner.deprovision_profile(mock_user)


class TestIsProvisioned:
    @pytest.mark.asyncio
    async def test_provisioned_when_mapped_and_exists(self, provisioner, mock_registry, mock_user):
        mock_registry.get_user_profile.return_value = "testuser"
        with patch("gateway.tenant.provisioner.profile_exists", return_value=True):
            assert await provisioner.is_provisioned(mock_user)

    @pytest.mark.asyncio
    async def test_not_provisioned_when_not_mapped(self, provisioner, mock_registry, mock_user):
        mock_registry.get_user_profile.return_value = None
        assert not await provisioner.is_provisioned(mock_user)

    @pytest.mark.asyncio
    async def test_not_provisioned_when_dir_missing(self, provisioner, mock_registry, mock_user):
        mock_registry.get_user_profile.return_value = "testuser"
        with patch("gateway.tenant.provisioner.profile_exists", return_value=False):
            assert not await provisioner.is_provisioned(mock_user)
