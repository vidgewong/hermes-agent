"""Claude Agent SDK isolation for multi-tenant sessions.

When the SDK runtime is active, each tenant's session gets scoped
ClaudeAgentOptions so settings, CLAUDE.md, memory, and working directory
context are per-tenant — complementing the physical Docker isolation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def get_tenant_sdk_env(profile_name: str) -> dict[str, str]:
    """Build environment overrides for a tenant's SDK session.

    These prevent cross-tenant contamination of settings, CLAUDE.md,
    and memory when the agent runs Claude Code SDK sessions.
    """
    from hermes_cli.profiles import get_profile_dir

    profile_dir = get_profile_dir(profile_name)
    claude_dir = profile_dir / ".claude"

    return {
        "CLAUDE_CONFIG_DIR": str(claude_dir),
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    }


def get_tenant_sdk_cwd(profile_name: str) -> str:
    """Get the working directory for a tenant's SDK session."""
    from hermes_cli.profiles import get_profile_dir

    profile_dir = get_profile_dir(profile_name)
    workspace_dir = profile_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return str(workspace_dir)


def apply_tenant_sdk_options(
    env: dict[str, str],
    profile_name: str,
) -> dict[str, str]:
    """Merge tenant SDK env overrides into an existing env dict.

    Returns the updated env dict (mutates in place and returns).
    """
    tenant_env = get_tenant_sdk_env(profile_name)
    env.update(tenant_env)
    return env
