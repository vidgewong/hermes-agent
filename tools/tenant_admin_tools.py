"""Tenant admin tools — manage users, identities, and profile provisioning.

Service-gated toolset: only exposed when multi_tenant is enabled AND the
current profile is in the admin_profiles list.  Handlers bridge the async
UserRegistry methods synchronously via asyncio so they fit the standard
tool-call contract (return JSON string).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict

from tools.registry import registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------


def _check_admin() -> bool:
    """Only expose tenant admin tools when current profile is in admin_profiles."""
    try:
        from hermes_cli.config import load_config

        config = load_config()
        mt_config = config.get("gateway", {}).get("multi_tenant", {})
        if not mt_config.get("enabled"):
            return False
        admin_profiles = mt_config.get("admin_profiles", ["default"])
        from hermes_cli.profiles import get_active_profile_name

        current = get_active_profile_name() or "default"
        return current in admin_profiles
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry():
    """Obtain a UserRegistry backed by the current tenant DB session factory."""
    from gateway.tenant.db import get_session_factory
    from gateway.tenant.registry import UserRegistry

    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Tenant database not initialized")
    return UserRegistry(factory)


def _run_async(coro):
    """Run an async coroutine synchronously (tool handlers are sync)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (gateway context).
        # Create a new loop in a thread to avoid nested run().
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def _user_to_dict(user) -> Dict[str, Any]:
    """Serialize a User ORM instance to a JSON-safe dict."""
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "wiw_id": user.wiw_id,
        "roles": user.roles or {},
        "responsibilities": user.responsibilities,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _identity_to_dict(identity) -> Dict[str, Any]:
    """Serialize an IMIdentity ORM instance to a JSON-safe dict."""
    return {
        "id": str(identity.id),
        "user_id": str(identity.user_id),
        "platform": identity.platform,
        "platform_user_id": identity.platform_user_id,
        "metadata": identity.metadata_ or {},
        "linked_at": identity.linked_at.isoformat() if identity.linked_at else None,
    }


def _profile_to_dict(profile) -> Dict[str, Any]:
    """Serialize a UserProfile ORM instance to a JSON-safe dict."""
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "profile_name": profile.profile_name,
        "is_primary": profile.is_primary,
        "provisioned_at": profile.provisioned_at.isoformat() if profile.provisioned_at else None,
    }


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _handle_user_list(args: Dict[str, Any], **kwargs) -> str:
    """List all registered tenant users."""
    try:
        reg = _get_registry()
        users = _run_async(reg.list_users())
        return json.dumps({"users": [_user_to_dict(u) for u in users]})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_user_get(args: Dict[str, Any], **kwargs) -> str:
    """Get user details by username or ID."""
    try:
        reg = _get_registry()
        identifier = args.get("identifier", "")

        # Try as UUID first
        try:
            user_id = uuid.UUID(identifier)
            user = _run_async(reg.get_user(user_id))
        except (ValueError, TypeError):
            # Fall back to username lookup
            user = _run_async(reg.get_user_by_username(identifier))
            if user is None:
                return json.dumps({"error": f"User '{identifier}' not found"})

        return json.dumps({"user": _user_to_dict(user)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_user_create(args: Dict[str, Any], **kwargs) -> str:
    """Create a new tenant user."""
    try:
        reg = _get_registry()
        user = _run_async(
            reg.create_user(
                username=args["username"],
                display_name=args.get("display_name"),
                email=args.get("email"),
                wiw_id=args.get("wiw_id"),
                roles=args.get("roles"),
                responsibilities=args.get("responsibilities"),
            )
        )
        return json.dumps({"user": _user_to_dict(user)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_user_update(args: Dict[str, Any], **kwargs) -> str:
    """Update user fields."""
    try:
        reg = _get_registry()
        user_id = uuid.UUID(args["user_id"])
        fields = {}
        for key in ("display_name", "email", "wiw_id", "roles", "responsibilities", "username"):
            if key in args and args[key] is not None:
                fields[key] = args[key]

        if not fields:
            return json.dumps({"error": "No fields to update"})

        user = _run_async(reg.update_user(user_id, **fields))
        return json.dumps({"user": _user_to_dict(user)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_user_link_identity(args: Dict[str, Any], **kwargs) -> str:
    """Link an IM identity (platform + platform_user_id) to a user."""
    try:
        reg = _get_registry()
        user_id = uuid.UUID(args["user_id"])
        identity = _run_async(
            reg.link_identity(
                user_id=user_id,
                platform=args["platform"],
                platform_user_id=args["platform_user_id"],
                metadata=args.get("metadata"),
            )
        )
        return json.dumps({"identity": _identity_to_dict(identity)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_user_provision(args: Dict[str, Any], **kwargs) -> str:
    """Provision (map) a Hermes profile for a user."""
    try:
        reg = _get_registry()
        user_id = uuid.UUID(args["user_id"])
        profile_name = args["profile_name"]
        is_primary = args.get("is_primary", True)

        profile = _run_async(
            reg.map_profile(
                user_id=user_id,
                profile_name=profile_name,
                is_primary=is_primary,
            )
        )
        return json.dumps({"profile": _profile_to_dict(profile)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Registry registrations
# ---------------------------------------------------------------------------

registry.register(
    name="user_list",
    toolset="tenant_admin",
    schema={
        "name": "user_list",
        "description": "List all registered multi-tenant users.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    handler=_handle_user_list,
    check_fn=_check_admin,
)

registry.register(
    name="user_get",
    toolset="tenant_admin",
    schema={
        "name": "user_get",
        "description": "Get user details by username or UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Username or user UUID to look up.",
                },
            },
            "required": ["identifier"],
        },
    },
    handler=_handle_user_get,
    check_fn=_check_admin,
)

registry.register(
    name="user_create",
    toolset="tenant_admin",
    schema={
        "name": "user_create",
        "description": "Create a new multi-tenant user.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Unique username for the new user.",
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable display name.",
                },
                "email": {
                    "type": "string",
                    "description": "Email address.",
                },
                "wiw_id": {
                    "type": "string",
                    "description": "External workforce/identity ID.",
                },
                "roles": {
                    "type": "object",
                    "description": "Role assignments (JSON object).",
                },
                "responsibilities": {
                    "type": "string",
                    "description": "Free-text description of user responsibilities.",
                },
            },
            "required": ["username"],
        },
    },
    handler=_handle_user_create,
    check_fn=_check_admin,
)

registry.register(
    name="user_update",
    toolset="tenant_admin",
    schema={
        "name": "user_update",
        "description": "Update fields on an existing multi-tenant user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "UUID of the user to update.",
                },
                "username": {
                    "type": "string",
                    "description": "New username.",
                },
                "display_name": {
                    "type": "string",
                    "description": "New display name.",
                },
                "email": {
                    "type": "string",
                    "description": "New email address.",
                },
                "wiw_id": {
                    "type": "string",
                    "description": "New external workforce/identity ID.",
                },
                "roles": {
                    "type": "object",
                    "description": "Updated role assignments.",
                },
                "responsibilities": {
                    "type": "string",
                    "description": "Updated responsibilities text.",
                },
            },
            "required": ["user_id"],
        },
    },
    handler=_handle_user_update,
    check_fn=_check_admin,
)

registry.register(
    name="user_link_identity",
    toolset="tenant_admin",
    schema={
        "name": "user_link_identity",
        "description": "Link an IM platform identity to a tenant user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "UUID of the user to link.",
                },
                "platform": {
                    "type": "string",
                    "description": "Platform name (e.g. telegram, feishu, slack).",
                },
                "platform_user_id": {
                    "type": "string",
                    "description": "User ID on the platform.",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata about the identity.",
                },
            },
            "required": ["user_id", "platform", "platform_user_id"],
        },
    },
    handler=_handle_user_link_identity,
    check_fn=_check_admin,
)

registry.register(
    name="user_provision",
    toolset="tenant_admin",
    schema={
        "name": "user_provision",
        "description": "Provision a Hermes profile for a tenant user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "UUID of the user to provision.",
                },
                "profile_name": {
                    "type": "string",
                    "description": "Name of the Hermes profile to map.",
                },
                "is_primary": {
                    "type": "boolean",
                    "description": "Whether this is the user's primary profile (default true).",
                },
            },
            "required": ["user_id", "profile_name"],
        },
    },
    handler=_handle_user_provision,
    check_fn=_check_admin,
)
