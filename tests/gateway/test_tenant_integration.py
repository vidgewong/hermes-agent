"""Integration tests for multi-tenant flow (Phase 10).

These tests verify the end-to-end tenant resolution pipeline using mocks
for the database layer, ensuring the gateway dispatch flow is correct.
"""

import dataclasses
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mt_config():
    return {
        "enabled": True,
        "database_url": "postgresql+asyncpg://localhost/test",
        "auto_register": True,
        "admin_profiles": ["default"],
        "profile_template": None,
        "container_idle_timeout": 3600,
    }


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "telegram_12345"
    return user


class TestFullResolutionFlow:
    """10.1 / 10.2: IM message → identity resolution → profile scoping."""

    @pytest.mark.asyncio
    async def test_known_user_resolves_to_profile(self, mt_config, mock_user):
        from gateway.tenant.resolver import TenantResolver

        registry = MagicMock()
        registry.resolve_by_im_identity = AsyncMock(return_value=mock_user)
        registry.get_user_profile = AsyncMock(return_value="telegram_12345")

        resolver = TenantResolver(registry, mt_config)
        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "12345", "dm"
        )

        assert user is mock_user
        assert profile == "telegram_12345"
        assert reject is None

    @pytest.mark.asyncio
    async def test_auto_registration_creates_user_and_profile(self, mt_config):
        from gateway.tenant.provisioner import TenantProvisioner
        from gateway.tenant.resolver import TenantResolver

        new_user = MagicMock()
        new_user.id = uuid.uuid4()
        new_user.username = "feishu_ou_abc"

        registry = MagicMock()
        registry.resolve_by_im_identity = AsyncMock(return_value=None)
        registry.create_user = AsyncMock(return_value=new_user)
        registry.link_identity = AsyncMock()
        registry.map_profile = AsyncMock()
        registry.get_user_profile = AsyncMock(return_value="feishu_ou_abc")
        registry.generate_username = MagicMock(return_value="feishu_ou_abc")

        provisioner = MagicMock()
        provisioner.provision_profile = AsyncMock(return_value="feishu_ou_abc")

        resolver = TenantResolver(registry, mt_config, provisioner=provisioner)
        user, profile, reject = await resolver.resolve_or_register(
            "feishu", "ou_abc", "private", {"display_name": "Test User"}
        )

        assert user is new_user
        assert profile == "feishu_ou_abc"
        assert reject is None
        provisioner.provision_profile.assert_awaited_once_with(new_user)


class TestAdminToolGating:
    """10.3: admin profile can use tools; tenant profile cannot."""

    def test_admin_check_passes_for_admin_profile(self):
        with patch("hermes_cli.config.load_config") as mock_config, \
             patch("hermes_cli.profiles.get_active_profile_name", return_value="default"):
            mock_config.return_value = {
                "gateway": {
                    "multi_tenant": {
                        "enabled": True,
                        "admin_profiles": ["default"],
                    }
                }
            }
            from tools.tenant_admin_tools import _check_admin
            assert _check_admin() is True

    def test_admin_check_fails_for_tenant_profile(self):
        with patch("hermes_cli.config.load_config") as mock_config, \
             patch("hermes_cli.profiles.get_active_profile_name", return_value="telegram_12345"):
            mock_config.return_value = {
                "gateway": {
                    "multi_tenant": {
                        "enabled": True,
                        "admin_profiles": ["default"],
                    }
                }
            }
            from tools.tenant_admin_tools import _check_admin
            assert _check_admin() is False

    def test_admin_check_fails_when_disabled(self):
        with patch("hermes_cli.config.load_config") as mock_config:
            mock_config.return_value = {
                "gateway": {"multi_tenant": {"enabled": False}}
            }
            from tools.tenant_admin_tools import _check_admin
            assert _check_admin() is False


class TestSingleUserModeUnaffected:
    """10.4: verify existing single-user mode is unaffected."""

    @pytest.mark.asyncio
    async def test_disabled_mode_skips_resolution(self):
        from gateway.tenant.resolver import TenantResolver

        config = {"enabled": False, "auto_register": False}
        registry = MagicMock()
        resolver = TenantResolver(registry, config)

        # DM-only gating still applies — but in disabled mode the gateway
        # never calls the resolver (tested at the gateway level, not here).
        # This test verifies the resolver doesn't crash when config is minimal.
        user, profile, reject = await resolver.resolve_or_register(
            "telegram", "999", "group"
        )
        assert user is None
        assert profile is None
        assert reject is None


class TestSDKIsolation:
    """10.6: two tenants' sessions have independent SDK config."""

    def test_tenant_sdk_env_isolation(self, tmp_path):
        with patch("hermes_cli.profiles.get_profile_dir") as mock_dir:
            mock_dir.side_effect = lambda name: tmp_path / "profiles" / name
            (tmp_path / "profiles" / "alice" / ".claude").mkdir(parents=True)
            (tmp_path / "profiles" / "bob" / ".claude").mkdir(parents=True)

            from gateway.tenant.sdk_isolation import get_tenant_sdk_env

            alice_env = get_tenant_sdk_env("alice")
            bob_env = get_tenant_sdk_env("bob")

            assert alice_env["CLAUDE_CONFIG_DIR"] != bob_env["CLAUDE_CONFIG_DIR"]
            assert "alice" in alice_env["CLAUDE_CONFIG_DIR"]
            assert "bob" in bob_env["CLAUDE_CONFIG_DIR"]
            assert alice_env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"

    def test_tenant_sdk_cwd_isolation(self, tmp_path):
        with patch("hermes_cli.profiles.get_profile_dir") as mock_dir:
            mock_dir.side_effect = lambda name: tmp_path / "profiles" / name

            from gateway.tenant.sdk_isolation import get_tenant_sdk_cwd

            alice_cwd = get_tenant_sdk_cwd("alice")
            bob_cwd = get_tenant_sdk_cwd("bob")

            assert alice_cwd != bob_cwd
            assert "alice" in alice_cwd
            assert "bob" in bob_cwd
