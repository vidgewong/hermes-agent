"""Map hermes provider configuration to Claude Code SDK options.

Claude Code CLI only supports a limited set of providers (Anthropic direct,
Bedrock, Vertex, OAuth). This module translates hermes' provider/api_key/model
into the env vars and CLI flags the SDK subprocess understands.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCodeProviderConfig:
    """Resolved configuration for passing to ClaudeAgentOptions."""

    model: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    extra_args: dict[str, str | None] = field(default_factory=dict)
    compatible: bool = True
    fallback_reason: str | None = None


def resolve_provider_for_sdk(agent) -> ClaudeCodeProviderConfig:
    """Translate hermes agent provider state into Claude Code SDK config.

    Returns a config that can be fed directly to ClaudeAgentOptions(env=...,
    model=..., extra_args=...).  When the provider is incompatible, returns
    compatible=False with a human-readable fallback_reason.
    """
    provider = getattr(agent, "provider", "") or ""
    model = getattr(agent, "model", "") or ""
    api_key = getattr(agent, "api_key", "") or ""
    base_url = getattr(agent, "base_url", "") or ""

    env: dict[str, str] = {}
    extra_args: dict[str, str | None] = {}

    # ─── Anthropic direct ─────────────────────────────────────────
    if provider == "anthropic" or (
        not provider and "api.anthropic.com" in base_url
    ):
        if isinstance(api_key, str) and api_key and api_key not in ("aws-sdk",):
            env["ANTHROPIC_API_KEY"] = api_key
        sdk_model = _strip_provider_prefix(model)
        return ClaudeCodeProviderConfig(
            model=sdk_model, env=env, extra_args=extra_args, compatible=True
        )

    # ─── Bedrock ──────────────────────────────────────────────────
    if provider == "bedrock" or "bedrock" in base_url.lower():
        # Pass through ALL Bedrock/AWS-related env vars — covers both
        # standard AWS credential chain and custom corporate setups
        # (bearer tokens, custom base URLs, proxies).
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_REGION",
            "AWS_DEFAULT_REGION",
            "AWS_PROFILE",
            "AWS_BEARER_TOKEN_BEDROCK",
            "ANTHROPIC_BEDROCK_BASE_URL",
            "ANTHROPIC_MODEL",
            "CLAUDE_CODE_USE_BEDROCK",
        ):
            val = os.environ.get(key)
            if val:
                env[key] = val
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"
        # Use the model name exactly as hermes has it — don't transform.
        # Bedrock environments may require specific model strings (e.g.
        # "claude-sonnet-4.6") that differ from SDK standard aliases.
        sdk_model = _strip_provider_prefix(model) if "/" in model else model
        if sdk_model:
            env["ANTHROPIC_MODEL"] = sdk_model
        return ClaudeCodeProviderConfig(
            model=sdk_model, env=env, extra_args=extra_args, compatible=True
        )

    # ─── Vertex AI ────────────────────────────────────────────────
    if provider == "vertex" or "vertex" in base_url.lower():
        for key in (
            "CLOUD_ML_REGION",
            "ANTHROPIC_VERTEX_PROJECT_ID",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
        ):
            val = os.environ.get(key)
            if val:
                env[key] = val
        env["CLAUDE_CODE_USE_VERTEX"] = "1"
        sdk_model = _strip_provider_prefix(model)
        return ClaudeCodeProviderConfig(
            model=sdk_model, env=env, extra_args=extra_args, compatible=True
        )

    # ─── Claude Code OAuth (reuse ~/.claude credentials) ──────────
    if provider in ("claude-code", ""):
        sdk_model = _strip_provider_prefix(model) if model else None
        return ClaudeCodeProviderConfig(
            model=sdk_model, env=env, extra_args=extra_args, compatible=True
        )

    # ─── Incompatible providers ───────────────────────────────────
    return ClaudeCodeProviderConfig(
        model=None,
        env={},
        extra_args={},
        compatible=False,
        fallback_reason=(
            f"Provider '{provider}' is not supported by Claude Code SDK. "
            f"Supported: anthropic, bedrock, vertex, claude-code (OAuth). "
            f"Falling back to hermes native runtime."
        ),
    )


def _strip_provider_prefix(model: str) -> str:
    """Strip hermes-style 'provider/model' prefix.

    'anthropic/claude-sonnet-4-5' → 'claude-sonnet-4-5'
    """
    if "/" in model:
        return model.split("/", 1)[1]
    return model
