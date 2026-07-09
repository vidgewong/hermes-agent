"""REST API endpoints for multi-tenant user management.

Mounts onto an existing aiohttp web.Application.  All endpoints require
Bearer token authentication (same API_SERVER_KEY as the main API server).

Usage from the gateway or API server startup:

    from gateway.tenant.api import mount_tenant_routes
    mount_tenant_routes(app, api_key="...")
"""

from __future__ import annotations

import hmac
import json
import logging
import uuid
from typing import Any, Dict, Optional

try:
    from aiohttp import web
except ImportError:
    web = None  # type: ignore[assignment]

from gateway.tenant.db import get_session_factory
from gateway.tenant.registry import UserRegistry, UserNotFoundError, UserRegistryError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _check_auth(request: "web.Request", api_key: str) -> Optional["web.Response"]:
    """Validate Bearer token. Returns None on success, 401 response on failure."""
    if not api_key:
        return None  # No key configured — open access (dev mode)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if hmac.compare_digest(token, api_key):
            return None

    return web.json_response(
        {"error": {"message": "Invalid API key", "type": "invalid_request_error"}},
        status=401,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry() -> UserRegistry:
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Tenant database not initialized")
    return UserRegistry(factory)


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
    return {
        "id": str(identity.id),
        "user_id": str(identity.user_id),
        "platform": identity.platform,
        "platform_user_id": identity.platform_user_id,
        "metadata": identity.metadata_ or {},
        "linked_at": identity.linked_at.isoformat() if identity.linked_at else None,
    }


def _profile_to_dict(profile) -> Dict[str, Any]:
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "profile_name": profile.profile_name,
        "is_primary": profile.is_primary,
        "provisioned_at": profile.provisioned_at.isoformat() if profile.provisioned_at else None,
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


class TenantRoutes:
    """Encapsulates tenant management REST handlers."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def _auth(self, request: "web.Request") -> Optional["web.Response"]:
        return _check_auth(request, self._api_key)

    # ------ Users ------

    async def handle_list_users(self, request: "web.Request") -> "web.Response":
        """GET /api/tenants/users"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            reg = _get_registry()
            users = await reg.list_users()
            return web.json_response({"users": [_user_to_dict(u) for u in users]})
        except Exception as e:
            logger.exception("Failed to list users")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_create_user(self, request: "web.Request") -> "web.Response":
        """POST /api/tenants/users"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            body = await request.json()
            username = body.get("username")
            if not username:
                return web.json_response(
                    {"error": "username is required"}, status=400
                )

            reg = _get_registry()
            user = await reg.create_user(
                username=username,
                display_name=body.get("display_name"),
                email=body.get("email"),
                wiw_id=body.get("wiw_id"),
                roles=body.get("roles"),
                responsibilities=body.get("responsibilities"),
            )
            return web.json_response({"user": _user_to_dict(user)}, status=201)
        except UserRegistryError as e:
            return web.json_response({"error": str(e)}, status=409)
        except Exception as e:
            logger.exception("Failed to create user")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_get_user(self, request: "web.Request") -> "web.Response":
        """GET /api/tenants/users/{user_id}"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            user_id_str = request.match_info["user_id"]
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                return web.json_response(
                    {"error": f"Invalid UUID: {user_id_str}"}, status=400
                )

            reg = _get_registry()
            user = await reg.get_user(user_id)
            return web.json_response({"user": _user_to_dict(user)})
        except UserNotFoundError as e:
            return web.json_response({"error": str(e)}, status=404)
        except Exception as e:
            logger.exception("Failed to get user")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_update_user(self, request: "web.Request") -> "web.Response":
        """PATCH /api/tenants/users/{user_id}"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            user_id_str = request.match_info["user_id"]
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                return web.json_response(
                    {"error": f"Invalid UUID: {user_id_str}"}, status=400
                )

            body = await request.json()
            fields = {}
            for key in ("username", "display_name", "email", "wiw_id", "roles", "responsibilities"):
                if key in body:
                    fields[key] = body[key]

            if not fields:
                return web.json_response(
                    {"error": "No updatable fields provided"}, status=400
                )

            reg = _get_registry()
            user = await reg.update_user(user_id, **fields)
            return web.json_response({"user": _user_to_dict(user)})
        except UserNotFoundError as e:
            return web.json_response({"error": str(e)}, status=404)
        except Exception as e:
            logger.exception("Failed to update user")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_delete_user(self, request: "web.Request") -> "web.Response":
        """DELETE /api/tenants/users/{user_id} — stub for future implementation."""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        return web.json_response(
            {"error": "User deletion not yet implemented"}, status=501
        )

    # ------ Identities ------

    async def handle_link_identity(self, request: "web.Request") -> "web.Response":
        """POST /api/tenants/users/{user_id}/identities"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            user_id_str = request.match_info["user_id"]
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                return web.json_response(
                    {"error": f"Invalid UUID: {user_id_str}"}, status=400
                )

            body = await request.json()
            platform = body.get("platform")
            platform_user_id = body.get("platform_user_id")
            if not platform or not platform_user_id:
                return web.json_response(
                    {"error": "platform and platform_user_id are required"},
                    status=400,
                )

            reg = _get_registry()
            identity = await reg.link_identity(
                user_id=user_id,
                platform=platform,
                platform_user_id=platform_user_id,
                metadata=body.get("metadata"),
            )
            return web.json_response(
                {"identity": _identity_to_dict(identity)}, status=201
            )
        except UserNotFoundError as e:
            return web.json_response({"error": str(e)}, status=404)
        except UserRegistryError as e:
            return web.json_response({"error": str(e)}, status=409)
        except Exception as e:
            logger.exception("Failed to link identity")
            return web.json_response({"error": str(e)}, status=500)

    # ------ Provisioning ------

    async def handle_provision(self, request: "web.Request") -> "web.Response":
        """POST /api/tenants/users/{user_id}/provision"""
        auth_err = self._auth(request)
        if auth_err:
            return auth_err
        try:
            user_id_str = request.match_info["user_id"]
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                return web.json_response(
                    {"error": f"Invalid UUID: {user_id_str}"}, status=400
                )

            body = await request.json()
            profile_name = body.get("profile_name")
            if not profile_name:
                return web.json_response(
                    {"error": "profile_name is required"}, status=400
                )

            is_primary = body.get("is_primary", True)

            reg = _get_registry()
            profile = await reg.map_profile(
                user_id=user_id,
                profile_name=profile_name,
                is_primary=is_primary,
            )
            return web.json_response(
                {"profile": _profile_to_dict(profile)}, status=201
            )
        except UserNotFoundError as e:
            return web.json_response({"error": str(e)}, status=404)
        except UserRegistryError as e:
            return web.json_response({"error": str(e)}, status=409)
        except Exception as e:
            logger.exception("Failed to provision profile")
            return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Mount helper
# ---------------------------------------------------------------------------


def mount_tenant_routes(app: "web.Application", api_key: str = "") -> None:
    """Register all tenant management routes on the given aiohttp app.

    Args:
        app: The aiohttp Application to mount routes on.
        api_key: Bearer token for authentication (same as API_SERVER_KEY).
    """
    routes = TenantRoutes(api_key=api_key)

    app.router.add_get("/api/tenants/users", routes.handle_list_users)
    app.router.add_post("/api/tenants/users", routes.handle_create_user)
    app.router.add_get("/api/tenants/users/{user_id}", routes.handle_get_user)
    app.router.add_patch("/api/tenants/users/{user_id}", routes.handle_update_user)
    app.router.add_delete("/api/tenants/users/{user_id}", routes.handle_delete_user)
    app.router.add_post(
        "/api/tenants/users/{user_id}/identities", routes.handle_link_identity
    )
    app.router.add_post(
        "/api/tenants/users/{user_id}/provision", routes.handle_provision
    )
