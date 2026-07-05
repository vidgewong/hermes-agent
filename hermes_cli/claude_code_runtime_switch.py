"""Shared logic for the /claude-code-runtime slash command.

Toggles api_mode between "auto" (hermes native) and "claude_code_sdk"
(hand turns to a Claude Code subprocess via the SDK).

Both CLI and gateway call into this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


VALID_RUNTIMES = ("auto", "claude_code_sdk")


@dataclass
class ClaudeCodeRuntimeStatus:
    """Result of a /claude-code-runtime invocation."""

    success: bool
    new_value: Optional[str] = None
    old_value: Optional[str] = None
    message: str = ""
    requires_new_session: bool = False
    sdk_available: bool = True
    cli_available: bool = True
    cli_version: Optional[str] = None


def parse_args(arg_string: str) -> tuple[Optional[str], list[str]]:
    """Parse the slash-command argument string.

    No args         → return current state (value=None)
    'on'/'claude-code'/'enable' → 'claude_code_sdk'
    'off'/'auto'/'hermes'       → 'auto'
    """
    raw = (arg_string or "").strip().lower()
    if not raw:
        return None, []
    if raw in {"on", "claude-code", "claude_code", "enable", "sdk"}:
        return "claude_code_sdk", []
    if raw in {"off", "auto", "default", "disable", "hermes", "native"}:
        return "auto", []
    if raw in VALID_RUNTIMES:
        return raw, []
    return None, [
        f"Unknown runtime {raw!r}. Use one of: auto, claude_code_sdk, on, off"
    ]


def get_current_runtime(config: dict) -> str:
    """Read the current claude_code_runtime value from config."""
    if not isinstance(config, dict):
        return "auto"
    model_cfg = config.get("model") or {}
    if not isinstance(model_cfg, dict):
        return "auto"
    value = str(model_cfg.get("claude_code_runtime") or "").strip().lower()
    if value in VALID_RUNTIMES:
        return value
    return "auto"


def set_runtime(config: dict, new_value: str) -> str:
    """Mutate config dict to persist the new runtime value. Returns previous."""
    if new_value not in VALID_RUNTIMES:
        raise ValueError(
            f"invalid runtime {new_value!r}; must be one of {VALID_RUNTIMES}"
        )
    old = get_current_runtime(config)
    if not isinstance(config.get("model"), dict):
        config["model"] = {}
    config["model"]["claude_code_runtime"] = new_value
    return old


def check_sdk_available(auto_install: bool = False) -> tuple[bool, Optional[str]]:
    """Check if claude-agent-sdk is importable, optionally auto-installing."""
    try:
        import claude_agent_sdk  # noqa: F401

        version = getattr(claude_agent_sdk, "__version__", "unknown")
        return True, version
    except ImportError:
        pass

    if auto_install:
        try:
            from tools.lazy_deps import ensure
            ensure("runtime.claude_code_sdk", prompt=False)
            import claude_agent_sdk  # noqa: F811

            version = getattr(claude_agent_sdk, "__version__", "unknown")
            return True, version
        except Exception:
            pass

    return False, None


def check_cli_available() -> tuple[bool, Optional[str]]:
    """Check if claude CLI is installed and accessible."""
    import shutil
    import subprocess

    cli_path = shutil.which("claude")
    if not cli_path:
        return False, None
    try:
        result = subprocess.run(
            [cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return True, version
    except Exception as exc:
        return False, str(exc)


def check_provider_compatible(config: dict) -> tuple[bool, str]:
    """Check if the current provider is compatible with Claude Code SDK."""
    from agent.claude_code_provider_bridge import resolve_provider_for_sdk

    class _FakeAgent:
        pass

    fake = _FakeAgent()
    model_cfg = config.get("model") or {}
    fake.provider = model_cfg.get("provider") or ""
    fake.model = model_cfg.get("default") or ""
    fake.api_key = ""
    fake.base_url = model_cfg.get("base_url") or ""

    result = resolve_provider_for_sdk(fake)
    if result.compatible:
        return True, "provider is compatible"
    return False, result.fallback_reason or "provider not supported"


def apply(
    config: dict,
    new_value: Optional[str],
    *,
    persist_callback=None,
) -> ClaudeCodeRuntimeStatus:
    """Top-level entry point used by both CLI and gateway handlers."""
    current = get_current_runtime(config)

    # Read-only call: just report state
    if new_value is None:
        sdk_ok, sdk_ver = check_sdk_available()
        cli_ok, cli_ver = check_cli_available()
        provider_ok, provider_msg = check_provider_compatible(config)

        lines = [
            f"claude_code_runtime: {current}",
            f"claude-agent-sdk: {'OK ' + (sdk_ver or '') if sdk_ok else 'not installed — pip install claude-agent-sdk'}",
            f"claude CLI: {'OK ' + (cli_ver or '') if cli_ok else 'not available — npm i -g @anthropic-ai/claude-code'}",
            f"provider: {'✓ ' + provider_msg if provider_ok else '✗ ' + provider_msg}",
        ]
        return ClaudeCodeRuntimeStatus(
            success=True,
            new_value=current,
            old_value=current,
            message="\n".join(lines),
            sdk_available=sdk_ok,
            cli_available=cli_ok,
            cli_version=cli_ver if cli_ok else None,
        )

    # No change
    if new_value == current:
        return ClaudeCodeRuntimeStatus(
            success=True,
            new_value=current,
            old_value=current,
            message=f"claude_code_runtime already set to {current}",
        )

    # Switching ON — verify prerequisites (auto-install SDK if missing)
    if new_value == "claude_code_sdk":
        sdk_ok, sdk_ver = check_sdk_available(auto_install=True)
        if not sdk_ok:
            return ClaudeCodeRuntimeStatus(
                success=False,
                old_value=current,
                message=(
                    "Cannot enable claude_code_sdk runtime: "
                    "claude-agent-sdk is not installed.\n"
                    "Install with: pip install claude-agent-sdk"
                ),
                sdk_available=False,
            )

        cli_ok, cli_ver = check_cli_available()
        if not cli_ok:
            return ClaudeCodeRuntimeStatus(
                success=False,
                old_value=current,
                message=(
                    "Cannot enable claude_code_sdk runtime: "
                    "claude CLI is not available.\n"
                    "Install with: npm i -g @anthropic-ai/claude-code"
                ),
                cli_available=False,
            )

        provider_ok, provider_msg = check_provider_compatible(config)
        if not provider_ok:
            return ClaudeCodeRuntimeStatus(
                success=False,
                old_value=current,
                message=(
                    f"Cannot enable claude_code_sdk runtime: {provider_msg}"
                ),
            )

    # Persist the change
    set_runtime(config, new_value)
    if persist_callback is not None:
        try:
            persist_callback(config)
        except Exception as exc:
            logger.exception("failed to persist claude_code_runtime change")
            return ClaudeCodeRuntimeStatus(
                success=False,
                new_value=new_value,
                old_value=current,
                message=f"updated config in memory but persist failed: {exc}",
            )

    # Build success message
    if new_value == "claude_code_sdk":
        _, cli_ver = check_cli_available()
        msg = (
            f"claude_code_runtime: {current} → {new_value}\n"
            f"claude CLI: {cli_ver}\n"
            "Turns now run through Claude Code SDK "
            "(Claude Code manages tool execution; "
            "hermes manages permissions and event routing).\n"
            "Effective on next session."
        )
    else:
        msg = (
            f"claude_code_runtime: {current} → {new_value}\n"
            "Turns will use the default hermes native runtime.\n"
            "Effective on next session."
        )

    return ClaudeCodeRuntimeStatus(
        success=True,
        new_value=new_value,
        old_value=current,
        message=msg,
        requires_new_session=True,
    )
