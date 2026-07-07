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
        # Config.yaml bedrock.bearer_token / bedrock.base_url take priority
        # over env vars — ensures the SDK subprocess uses centrally managed
        # credentials even when env vars are stale or absent.
        try:
            from hermes_cli.config import load_config as _lc_bedrock
            _bedrock_cfg = _lc_bedrock().get("bedrock", {})
            _cfg_bearer = str(_bedrock_cfg.get("bearer_token") or "").strip()
            _cfg_base = str(_bedrock_cfg.get("base_url") or "").strip()
            if _cfg_bearer:
                env["AWS_BEARER_TOKEN_BEDROCK"] = _cfg_bearer
            if _cfg_base:
                env["ANTHROPIC_BEDROCK_BASE_URL"] = _cfg_base
        except Exception:
            pass
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

    # ─── Custom / LiteLLM proxy ───────────────────────────────────
    # Hermes-resolved credentials (from custom_providers in config.yaml) take
    # priority over env vars so stale ANTHROPIC_* values can't override them.
    if provider == "custom" or not provider:
        if api_key and api_key not in ("no-key-required",):
            env["ANTHROPIC_API_KEY"] = api_key
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url
        sdk_model = _strip_provider_prefix(model) if model else None
        if sdk_model:
            env["ANTHROPIC_MODEL"] = sdk_model
        # Propagate ssl_verify: false → NODE_TLS_REJECT_UNAUTHORIZED=0 for the
        # Node.js Claude CLI subprocess (Python ssl_verify is handled separately
        # by the httpx client built in auxiliary_client.py).
        if base_url:
            try:
                from hermes_cli.config import get_custom_provider_tls_settings, load_config as _lc
                _cfg = _lc()
                _tls = get_custom_provider_tls_settings(base_url, _cfg.get("custom_providers"), _cfg)
                if _tls.get("ssl_verify") is False:
                    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            except Exception:
                pass
        # Fill any remaining gaps from the environment.
        for key in (
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_MODEL",
            "NODE_TLS_REJECT_UNAUTHORIZED",
        ):
            if not env.get(key):
                val = os.environ.get(key)
                if val:
                    env[key] = val
        return ClaudeCodeProviderConfig(
            model=None, env=env, extra_args=extra_args, compatible=True
        )

    # ─── Incompatible providers ───────────────────────────────────
    return ClaudeCodeProviderConfig(
        model=None,
        env={},
        extra_args={},
        compatible=False,
        fallback_reason=(
            f"Provider '{provider}' is not supported by Claude Code SDK. "
            f"Supported: anthropic, bedrock, vertex, claude-code (OAuth), custom. "
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
