"""CLI subcommands for multi-tenant user management (hermes tenant ...).

Provides registration, identity linking, profile provisioning, and status
reporting for the multi-tenant gateway mode.  All DB work is delegated to
gateway.tenant.db / gateway.tenant.registry.  This module is wired into
argparse by main.py.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_mt_config() -> dict[str, Any]:
    """Load and return the gateway.multi_tenant config section."""
    from hermes_cli.config import load_config

    cfg = load_config()
    return cfg.get("gateway", {}).get("multi_tenant", {})


def _require_enabled(mt_cfg: dict[str, Any]) -> bool:
    """Check that multi-tenant is enabled. Prints error and returns False if not."""
    if not mt_cfg.get("enabled"):
        print(
            "Error: multi-tenant mode is not enabled.\n"
            "Set gateway.multi_tenant.enabled: true in config.yaml.",
            file=sys.stderr,
        )
        return False
    return True


def _get_database_url(mt_cfg: dict[str, Any]) -> str | None:
    """Extract and validate database_url from config."""
    url = mt_cfg.get("database_url", "")
    if not url:
        print(
            "Error: gateway.multi_tenant.database_url is not configured.\n"
            "Set a PostgreSQL connection string in config.yaml.",
            file=sys.stderr,
        )
        return None
    return url


async def _init_and_get_registry(mt_cfg: dict[str, Any]):
    """Initialize DB and return a UserRegistry instance. Returns None on failure."""
    from gateway.tenant.db import get_session_factory, init_db
    from gateway.tenant.registry import UserRegistry

    url = _get_database_url(mt_cfg)
    if not url:
        return None

    try:
        await init_db(url)
    except Exception as exc:
        print(f"Error: could not connect to database: {exc}", file=sys.stderr)
        return None

    factory = get_session_factory()
    if factory is None:
        print("Error: session factory not available after init_db()", file=sys.stderr)
        return None

    return UserRegistry(factory)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_list(args: argparse.Namespace) -> int:
    """List all registered tenant users."""
    mt_cfg = _get_mt_config()
    if not _require_enabled(mt_cfg):
        return 1

    async def _run():
        registry = await _init_and_get_registry(mt_cfg)
        if registry is None:
            return 1

        from gateway.tenant.db import get_session_factory
        from gateway.tenant.models import IMIdentity, UserProfile
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Fetch users with their relationships eagerly loaded
        factory = get_session_factory()
        async with factory() as session:
            from gateway.tenant.models import User

            result = await session.execute(
                select(User)
                .options(selectinload(User.identities), selectinload(User.profiles))
                .order_by(User.created_at)
            )
            users = list(result.scalars().all())

        if not users:
            print("No tenant users registered.")
            return 0

        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="Tenant Users")
            table.add_column("Username", style="cyan", no_wrap=True)
            table.add_column("Display Name", style="green")
            table.add_column("Email")
            table.add_column("Profile", style="yellow")
            table.add_column("Identities", style="magenta")

            for user in users:
                profile_names = ", ".join(
                    p.profile_name for p in (user.profiles or [])
                ) or "(none)"
                identity_strs = ", ".join(
                    f"{ident.platform}:{ident.platform_user_id}"
                    for ident in (user.identities or [])
                ) or "(none)"
                table.add_row(
                    user.username,
                    user.display_name or "",
                    user.email or "",
                    profile_names,
                    identity_strs,
                )

            console.print(table)
        except ImportError:
            # Fallback without rich
            print(f"{'Username':<20} {'Display Name':<20} {'Profile':<20} {'Identities'}")
            print("-" * 80)
            for user in users:
                profile_names = ", ".join(
                    p.profile_name for p in (user.profiles or [])
                ) or "(none)"
                identity_strs = ", ".join(
                    f"{ident.platform}:{ident.platform_user_id}"
                    for ident in (user.identities or [])
                ) or "(none)"
                print(
                    f"{user.username:<20} {user.display_name or '':<20} "
                    f"{profile_names:<20} {identity_strs}"
                )

        return 0

    return asyncio.run(_run())


def _cmd_add(args: argparse.Namespace) -> int:
    """Create a new tenant user and optionally provision a profile."""
    mt_cfg = _get_mt_config()
    if not _require_enabled(mt_cfg):
        return 1

    username = args.username

    async def _run():
        registry = await _init_and_get_registry(mt_cfg)
        if registry is None:
            return 1

        # Check if user already exists
        existing = await registry.get_user_by_username(username)
        if existing:
            print(f"Error: user '{username}' already exists.", file=sys.stderr)
            return 1

        # Create user
        try:
            user = await registry.create_user(
                username=username,
                display_name=getattr(args, "display_name", None),
                email=getattr(args, "email", None),
            )
        except Exception as exc:
            print(f"Error creating user: {exc}", file=sys.stderr)
            return 1

        print(f"Created user '{username}' (id={user.id})")

        # Provision profile
        from gateway.tenant.provisioner import TenantProvisioner

        provisioner = TenantProvisioner(registry, mt_cfg)
        template = getattr(args, "template", None)
        try:
            profile_name = await provisioner.provision_profile(user, template=template)
            print(f"Provisioned profile '{profile_name}' for user '{username}'")
        except Exception as exc:
            print(f"Warning: profile provisioning failed: {exc}", file=sys.stderr)
            print("User created but profile not provisioned. Use 'hermes tenant provision' to retry.")

        return 0

    return asyncio.run(_run())


def _cmd_remove(args: argparse.Namespace) -> int:
    """Remove a tenant user record (profile directory is preserved)."""
    mt_cfg = _get_mt_config()
    if not _require_enabled(mt_cfg):
        return 1

    username = args.username

    async def _run():
        registry = await _init_and_get_registry(mt_cfg)
        if registry is None:
            return 1

        user = await registry.get_user_by_username(username)
        if not user:
            print(f"Error: user '{username}' not found.", file=sys.stderr)
            return 1

        # Warn about profile preservation
        profile_name = await registry.get_user_profile(user.id)
        if profile_name:
            print(
                f"Warning: profile directory '{profile_name}' will NOT be deleted.\n"
                "  Use 'hermes profile remove' separately if you want to remove it."
            )

        # Delete the user record (cascades to identities + profile mappings)
        from gateway.tenant.db import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            user_obj = await session.get(type(user), user.id)
            if user_obj:
                await session.delete(user_obj)
                await session.commit()

        print(f"Removed user '{username}' from tenant registry.")
        return 0

    return asyncio.run(_run())


def _cmd_link(args: argparse.Namespace) -> int:
    """Link an IM identity to a tenant user."""
    mt_cfg = _get_mt_config()
    if not _require_enabled(mt_cfg):
        return 1

    username = args.username
    platform = args.platform
    platform_user_id = args.platform_user_id

    async def _run():
        registry = await _init_and_get_registry(mt_cfg)
        if registry is None:
            return 1

        user = await registry.get_user_by_username(username)
        if not user:
            print(f"Error: user '{username}' not found.", file=sys.stderr)
            return 1

        try:
            identity = await registry.link_identity(
                user_id=user.id,
                platform=platform,
                platform_user_id=platform_user_id,
            )
        except Exception as exc:
            print(f"Error linking identity: {exc}", file=sys.stderr)
            return 1

        print(
            f"Linked identity {platform}:{platform_user_id} to user '{username}' "
            f"(identity_id={identity.id})"
        )
        return 0

    return asyncio.run(_run())


def _cmd_provision(args: argparse.Namespace) -> int:
    """Provision or re-provision a profile for an existing tenant user."""
    mt_cfg = _get_mt_config()
    if not _require_enabled(mt_cfg):
        return 1

    username = args.username

    async def _run():
        registry = await _init_and_get_registry(mt_cfg)
        if registry is None:
            return 1

        user = await registry.get_user_by_username(username)
        if not user:
            print(f"Error: user '{username}' not found.", file=sys.stderr)
            return 1

        from gateway.tenant.provisioner import TenantProvisioner

        provisioner = TenantProvisioner(registry, mt_cfg)
        template = getattr(args, "template", None)
        try:
            profile_name = await provisioner.provision_profile(user, template=template)
            print(f"Provisioned profile '{profile_name}' for user '{username}'")
        except Exception as exc:
            print(f"Error provisioning profile: {exc}", file=sys.stderr)
            return 1

        return 0

    return asyncio.run(_run())


def _cmd_status(args: argparse.Namespace) -> int:
    """Show multi-tenant system status."""
    mt_cfg = _get_mt_config()

    enabled = mt_cfg.get("enabled", False)
    db_url = mt_cfg.get("database_url", "")

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
    except ImportError:
        console = None

    status_lines = []
    status_lines.append(("Multi-tenant mode", "ENABLED" if enabled else "DISABLED"))
    status_lines.append(("Database URL", _redact_url(db_url) if db_url else "(not configured)"))
    status_lines.append(("Auto-register", str(mt_cfg.get("auto_register", True))))
    status_lines.append(("Admin profiles", ", ".join(mt_cfg.get("admin_profiles", ["default"]))))
    status_lines.append(("Profile template", mt_cfg.get("profile_template") or "(none)"))
    status_lines.append((
        "Container idle timeout",
        f"{mt_cfg.get('container_idle_timeout', 3600)}s",
    ))

    # Attempt DB connection check and user count
    db_status = "unknown"
    user_count = "?"
    if enabled and db_url:
        try:
            async def _check():
                from gateway.tenant.db import get_session_factory, init_db
                from gateway.tenant.registry import UserRegistry

                await init_db(db_url)
                factory = get_session_factory()
                if factory is None:
                    return "error", "?"
                reg = UserRegistry(factory)
                users = await reg.list_users()
                return "connected", str(len(users))

            db_status, user_count = asyncio.run(_check())
        except Exception as exc:
            db_status = f"error: {exc}"
            user_count = "?"

    status_lines.append(("DB connection", db_status))
    status_lines.append(("Registered users", user_count))

    if console:
        table = Table(title="Multi-Tenant Status", show_header=False)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        for key, value in status_lines:
            # Color disabled/error states differently
            style = None
            if value == "DISABLED":
                style = "red"
            elif value == "ENABLED":
                style = "green bold"
            elif value.startswith("error"):
                style = "red"
            table.add_row(key, value, style=style)
        console.print(table)
    else:
        for key, value in status_lines:
            print(f"  {key}: {value}")

    return 0


def _redact_url(url: str) -> str:
    """Redact password from a database URL for display."""
    import re

    # Redact password in postgresql://user:password@host/db patterns
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1****\2", url)


# ---------------------------------------------------------------------------
# Argparse builder
# ---------------------------------------------------------------------------


def register_cli(parent: argparse.ArgumentParser) -> None:
    """Attach ``tenant`` subcommands to *parent*.

    main.py calls this with the ArgumentParser returned by
    ``subparsers.add_parser("tenant", ...)``.
    """
    parent.set_defaults(func=lambda a: (parent.print_help(), 0)[1])
    subs = parent.add_subparsers(dest="tenant_command")

    # --- list ---
    p_list = subs.add_parser(
        "list", aliases=["ls"],
        help="Show all registered users with profiles and identities",
    )
    p_list.set_defaults(func=_cmd_list)

    # --- add ---
    p_add = subs.add_parser(
        "add",
        help="Create a new tenant user and provision a profile",
    )
    p_add.add_argument("username", help="Unique username for the tenant")
    p_add.add_argument(
        "--display-name", dest="display_name", default=None,
        help="Human-readable display name",
    )
    p_add.add_argument(
        "--email", default=None,
        help="Contact email address",
    )
    p_add.add_argument(
        "--template", default=None,
        help="Profile template to clone from (overrides config default)",
    )
    p_add.set_defaults(func=_cmd_add)

    # --- remove ---
    p_remove = subs.add_parser(
        "remove", aliases=["rm"],
        help="Remove a user record (profile directory is preserved)",
    )
    p_remove.add_argument("username", help="Username to remove")
    p_remove.set_defaults(func=_cmd_remove)

    # --- link ---
    p_link = subs.add_parser(
        "link",
        help="Link an IM identity to a user (for gateway routing)",
    )
    p_link.add_argument("username", help="Username to link to")
    p_link.add_argument("platform", help="Platform name (e.g. telegram, discord, feishu)")
    p_link.add_argument("platform_user_id", help="User ID on the platform")
    p_link.set_defaults(func=_cmd_link)

    # --- provision ---
    p_provision = subs.add_parser(
        "provision",
        help="Provision/re-provision a profile for an existing user",
    )
    p_provision.add_argument("username", help="Username to provision")
    p_provision.add_argument(
        "--template", default=None,
        help="Profile template to clone from (overrides config default)",
    )
    p_provision.set_defaults(func=_cmd_provision)

    # --- status ---
    p_status = subs.add_parser(
        "status",
        help="Show multi-tenant system status (enabled, DB, user count)",
    )
    p_status.set_defaults(func=_cmd_status)
