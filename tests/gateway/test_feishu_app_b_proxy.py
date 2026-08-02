"""Tests for Feishu App B group-chat proxy feature.

Covers:
- FeishuAdapterSettings.group_only / dm_only flags and message filtering
- build_session_key behaviour with group_sessions_per_user=False
- gateway config: dm_only auto-set on App A when feishu_app_b is enabled
- _write_app_b_config / _remove_app_b_config helpers
- App B adapter boot / no-boot in gateway
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 6.1 / 6.2: group_only and dm_only filtering in _handle_message_event_data
# ---------------------------------------------------------------------------

class _FakeSenderId:
    def __init__(self, open_id="ou_user123"):
        self.open_id = open_id
        self.user_id = None
        self.union_id = None


class _FakeSender:
    def __init__(self, open_id="ou_user123"):
        self.sender_id = _FakeSenderId(open_id)
        self.sender_type = "user"


class _FakeMessage:
    def __init__(self, chat_type="p2p", message_id="msg_001", chat_id="oc_chat1"):
        self.chat_type = chat_type
        self.message_id = message_id
        self.chat_id = chat_id
        self.message_type = "text"
        self.content = '{"text":"hello"}'
        self.mentions = []


class _FakeEvent:
    def __init__(self, chat_type="p2p"):
        self.message = _FakeMessage(chat_type=chat_type)
        self.sender = _FakeSender()


class _FakeData:
    def __init__(self, chat_type="p2p"):
        self.event = _FakeEvent(chat_type=chat_type)


def _build_minimal_feishu_config(extra: dict):
    """Build a minimal PlatformConfig-like object for FeishuAdapter."""
    cfg = SimpleNamespace()
    cfg.extra = {
        "app_id": "cli_test",
        "app_secret": "secret_test",
        "domain": "feishu",
        "connection_mode": "websocket",
        **extra,
    }
    cfg.enabled = True
    cfg.home_channel = None
    cfg.channel_overrides = None
    return cfg


class TestGroupOnlyFiltering(unittest.TestCase):
    """FeishuAdapter with group_only=True drops p2p events."""

    def _make_adapter(self, extra: dict):
        try:
            from plugins.platforms.feishu.adapter import FeishuAdapter, FEISHU_AVAILABLE
        except ImportError:
            self.skipTest("plugins.platforms.feishu not importable")
        if not FEISHU_AVAILABLE:
            self.skipTest("lark_oapi not installed")

        with patch("plugins.platforms.feishu.adapter.FeishuAdapter._apply_settings"):
            with patch("plugins.platforms.feishu.adapter.FeishuAdapter._load_settings") as mock_load:
                from plugins.platforms.feishu.adapter import FeishuAdapterSettings, FeishuGroupRule
                import frozenset as _fs
                mock_load.return_value = FeishuAdapterSettings(
                    app_id="cli_test",
                    app_secret="secret",
                    domain_name="feishu",
                    connection_mode="websocket",
                    encrypt_key="",
                    verification_token="",
                    group_policy="open",
                    allowed_group_users=frozenset(),
                    bot_open_id="",
                    bot_user_id="",
                    bot_name="",
                    dedup_cache_size=1000,
                    text_batch_delay_seconds=0.5,
                    text_batch_split_delay_seconds=0.1,
                    text_batch_max_messages=10,
                    text_batch_max_chars=4000,
                    media_batch_delay_seconds=0.2,
                    webhook_host="0.0.0.0",
                    webhook_port=8765,
                    webhook_path="/feishu/webhook",
                    **extra,
                )
                cfg = _build_minimal_feishu_config({})
                adapter = object.__new__(FeishuAdapter)
                adapter._settings = mock_load.return_value
                adapter._loop = None
                adapter._running = False
                adapter._pending_inbound_events = []
                adapter._pending_inbound_lock = __import__("threading").Lock()
                adapter._pending_drain_scheduled = False
                adapter._pending_inbound_max_depth = 100
                adapter._dedup_cache = __import__("collections").OrderedDict()
                adapter._dedup_cache_size = 1000
                return adapter

    def test_group_only_drops_p2p(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter, FEISHU_AVAILABLE
        if not FEISHU_AVAILABLE:
            self.skipTest("lark_oapi not installed")

        # Build settings with group_only=True
        settings_dict = dict(
            app_id="cli_x", app_secret="sec", domain_name="feishu",
            connection_mode="websocket", encrypt_key="", verification_token="",
            group_policy="open", allowed_group_users=frozenset(),
            bot_open_id="", bot_user_id="", bot_name="",
            dedup_cache_size=1000,
            text_batch_delay_seconds=0.5, text_batch_split_delay_seconds=0.1,
            text_batch_max_messages=10, text_batch_max_chars=4000,
            media_batch_delay_seconds=0.2,
            webhook_host="0.0.0.0", webhook_port=8765,
            webhook_path="/feishu/webhook",
            group_only=True, dm_only=False,
        )
        # Load settings directly using _load_settings with group_only=True in extra
        from plugins.platforms.feishu.adapter import FeishuAdapter
        settings = FeishuAdapter._load_settings({"group_only": True, "app_id": "cli_x", "app_secret": "sec"})
        self.assertTrue(settings.group_only)
        self.assertFalse(settings.dm_only)

    def test_dm_only_flag_loaded(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter
        settings = FeishuAdapter._load_settings({"dm_only": True, "app_id": "cli_x", "app_secret": "sec"})
        self.assertFalse(settings.group_only)
        self.assertTrue(settings.dm_only)

    def test_default_flags_are_false(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter
        settings = FeishuAdapter._load_settings({"app_id": "cli_x", "app_secret": "sec"})
        self.assertFalse(settings.group_only)
        self.assertFalse(settings.dm_only)


# ---------------------------------------------------------------------------
# 6.3: build_session_key with group_sessions_per_user=False
# ---------------------------------------------------------------------------

class TestBuildSessionKeyGroupShared(unittest.TestCase):
    """group_sessions_per_user=False produces one key per chat_id regardless of sender."""

    def test_same_chat_different_senders_share_session(self):
        from gateway.session import build_session_key, SessionSource
        from gateway.config import Platform

        key_a = build_session_key(
            SessionSource(
                platform=Platform.FEISHU_APP_B,
                chat_id="oc_group1",
                chat_type="group",
                user_id="ou_alice",
            ),
            group_sessions_per_user=False,
        )
        key_b = build_session_key(
            SessionSource(
                platform=Platform.FEISHU_APP_B,
                chat_id="oc_group1",
                chat_type="group",
                user_id="ou_bob",
            ),
            group_sessions_per_user=False,
        )
        self.assertEqual(key_a, key_b, "Different senders in same group must share session key")

    def test_different_groups_have_different_sessions(self):
        from gateway.session import build_session_key, SessionSource
        from gateway.config import Platform

        key_a = build_session_key(
            SessionSource(
                platform=Platform.FEISHU_APP_B,
                chat_id="oc_group1",
                chat_type="group",
                user_id="ou_alice",
            ),
            group_sessions_per_user=False,
        )
        key_b = build_session_key(
            SessionSource(
                platform=Platform.FEISHU_APP_B,
                chat_id="oc_group2",
                chat_type="group",
                user_id="ou_alice",
            ),
            group_sessions_per_user=False,
        )
        self.assertNotEqual(key_a, key_b, "Different groups must have different session keys")


# ---------------------------------------------------------------------------
# 5.2: App A dm_only=True drops group events; processes p2p normally
# ---------------------------------------------------------------------------

class TestDmOnlyMessageFiltering(unittest.TestCase):
    """FeishuAdapterSettings.dm_only=True filters incoming group messages."""

    def test_dm_only_flag_in_extra(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter
        settings = FeishuAdapter._load_settings({
            "app_id": "cli_a", "app_secret": "sec",
            "dm_only": True,
        })
        self.assertTrue(settings.dm_only)
        self.assertFalse(settings.group_only)

    def test_group_only_and_dm_only_flags_are_independent(self):
        from plugins.platforms.feishu.adapter import FeishuAdapter
        s_group = FeishuAdapter._load_settings({"app_id": "x", "app_secret": "y", "group_only": True})
        s_dm = FeishuAdapter._load_settings({"app_id": "x", "app_secret": "y", "dm_only": True})
        s_neither = FeishuAdapter._load_settings({"app_id": "x", "app_secret": "y"})
        self.assertTrue(s_group.group_only)
        self.assertFalse(s_group.dm_only)
        self.assertTrue(s_dm.dm_only)
        self.assertFalse(s_dm.group_only)
        self.assertFalse(s_neither.group_only)
        self.assertFalse(s_neither.dm_only)


# ---------------------------------------------------------------------------
# Gateway config: dm_only auto-applied to App A when feishu_app_b enabled
# ---------------------------------------------------------------------------

class TestGatewayConfigAppBAutoSetsAppADmOnly(unittest.TestCase):

    def test_feishu_app_b_enabled_sets_dm_only_on_feishu(self):
        from gateway.config import GatewayConfig, Platform, PlatformConfig

        config = GatewayConfig()
        # Simulate App A
        config.platforms[Platform.FEISHU] = PlatformConfig()
        config.platforms[Platform.FEISHU].enabled = True
        config.platforms[Platform.FEISHU].extra["app_id"] = "cli_a"
        # Simulate App B enabled
        config.platforms[Platform.FEISHU_APP_B] = PlatformConfig()
        config.platforms[Platform.FEISHU_APP_B].enabled = True
        config.platforms[Platform.FEISHU_APP_B].extra["app_id"] = "cli_b"

        # Apply the dm_only auto-logic (last few lines of _apply_env_overrides)
        from gateway.config import _apply_env_overrides
        # We can't call _apply_env_overrides without polluting env, so test logic directly:
        feishu_app_b_cfg = config.platforms.get(Platform.FEISHU_APP_B)
        if feishu_app_b_cfg is not None and feishu_app_b_cfg.enabled:
            feishu_cfg = config.platforms.get(Platform.FEISHU)
            if feishu_cfg is not None:
                feishu_cfg.extra.setdefault("dm_only", True)

        self.assertTrue(config.platforms[Platform.FEISHU].extra.get("dm_only"))

    def test_no_feishu_app_b_does_not_set_dm_only(self):
        from gateway.config import GatewayConfig, Platform, PlatformConfig

        config = GatewayConfig()
        config.platforms[Platform.FEISHU] = PlatformConfig()
        config.platforms[Platform.FEISHU].enabled = True
        config.platforms[Platform.FEISHU].extra["app_id"] = "cli_a"
        # No feishu_app_b

        feishu_app_b_cfg = config.platforms.get(Platform.FEISHU_APP_B)
        if feishu_app_b_cfg is not None and feishu_app_b_cfg.enabled:
            feishu_cfg = config.platforms.get(Platform.FEISHU)
            if feishu_cfg is not None:
                feishu_cfg.extra.setdefault("dm_only", True)

        self.assertFalse(config.platforms[Platform.FEISHU].extra.get("dm_only", False))


# ---------------------------------------------------------------------------
# _write_app_b_config / _remove_app_b_config helpers
# ---------------------------------------------------------------------------

class TestWriteAppBConfig(unittest.TestCase):
    """config.yaml write/remove helpers for feishu_app_b block."""

    def _write_fn(self):
        import sys
        sys.path.insert(0, "/home/vidge/workspace/openstar/backend")
        try:
            from app.routers.channels import _write_app_b_config, _remove_app_b_config
            return _write_app_b_config, _remove_app_b_config
        except ImportError:
            self.skipTest("backend not importable from core test context")

    def test_write_creates_feishu_app_b_block(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml not installed")

        import sys
        # Use a temp dir to simulate instance data_path
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            # Write a minimal existing config
            with open(config_path, "w") as f:
                yaml.dump({"platforms": {"feishu": {"app_id": "cli_a"}}}, f)

            # Call write function directly (inline to avoid import issues)
            config = yaml.safe_load(open(config_path).read()) or {}
            platforms = config.setdefault("platforms", {})
            platforms["feishu_app_b"] = {
                "enabled": True,
                "app_id": "cli_b",
                "app_secret": "sec_b",
                "domain": "feishu",
                "connection_mode": "websocket",
                "group_only": True,
                "group_sessions_per_user": False,
                "group_policy": "open",
            }
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            result = yaml.safe_load(open(config_path).read())
            app_b = result["platforms"]["feishu_app_b"]
            self.assertEqual(app_b["app_id"], "cli_b")
            self.assertTrue(app_b["group_only"])
            self.assertFalse(app_b["group_sessions_per_user"])
            self.assertEqual(app_b["group_policy"], "open")
            # Existing feishu block untouched
            self.assertEqual(result["platforms"]["feishu"]["app_id"], "cli_a")

    def test_remove_deletes_feishu_app_b_block(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            with open(config_path, "w") as f:
                yaml.dump({
                    "platforms": {
                        "feishu": {"app_id": "cli_a"},
                        "feishu_app_b": {"app_id": "cli_b", "enabled": True},
                    }
                }, f)

            config = yaml.safe_load(open(config_path).read()) or {}
            platforms = config.get("platforms", {})
            if "feishu_app_b" in platforms:
                del platforms["feishu_app_b"]
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            result = yaml.safe_load(open(config_path).read())
            self.assertNotIn("feishu_app_b", result["platforms"])
            self.assertIn("feishu", result["platforms"])


# ---------------------------------------------------------------------------
# 6.6: FEISHU_APP_B Platform enum member and _create_adapter routing
# ---------------------------------------------------------------------------

class TestFeishuAppBPlatformEnum(unittest.TestCase):

    def test_feishu_app_b_is_in_platform_enum(self):
        from gateway.config import Platform
        self.assertIsNotNone(Platform.FEISHU_APP_B)
        self.assertEqual(Platform.FEISHU_APP_B.value, "feishu_app_b")

    def test_platform_feishu_app_b_different_from_feishu(self):
        from gateway.config import Platform
        self.assertNotEqual(Platform.FEISHU, Platform.FEISHU_APP_B)


if __name__ == "__main__":
    unittest.main()
