"""Send file tool — delivers a file from the workspace to the user via messaging platform."""

import json
import os
from pathlib import Path

from tools.registry import registry


def _check_send_file_requirements() -> bool:
    """Available when running in a gateway session."""
    return os.environ.get("_HERMES_GATEWAY") == "1"


def send_file_tool(file_path: str, task_id: str = None, session_id: str = None, **kwargs) -> str:
    """Send a file to the user as a native platform attachment.

    For tenant containers, translates the container path to the host path
    and queues it for delivery via the platform adapter.
    """
    if not file_path or not file_path.strip():
        return json.dumps({"error": "file_path is required"})

    file_path = file_path.strip()

    # Resolve tenant container path → host path
    host_path = _resolve_to_host_path(file_path)

    if not host_path or not Path(host_path).is_file():
        return json.dumps({
            "error": f"File not found: {file_path}",
            "hint": "Ensure the file exists in your workspace before sending.",
        })

    size = Path(host_path).stat().st_size

    # Return MEDIA: tag so the gateway auto-append mechanism picks it up
    # and delivers it as a native attachment.
    return json.dumps({
        "success": True,
        "file": file_path,
        "host_path": host_path,
        "size_bytes": size,
        "delivery": f"MEDIA:{host_path}",
    })


def _resolve_to_host_path(container_path: str) -> str | None:
    """Translate a container path to the host filesystem path.

    Mapping: /home/<username>/workspace/X → ~/.hermes/profiles/<profile>/workspace/X
    Falls through to checking the path directly on host if no translation needed.
    """
    # Direct host path (non-tenant or already resolved)
    if Path(container_path).is_file():
        return container_path

    # Expand ~ paths
    expanded = str(Path(container_path).expanduser())
    if Path(expanded).is_file():
        return expanded

    # Tenant container path translation
    # Pattern: /home/<username>/workspace/... or ~/workspace/...
    path_str = container_path
    parts = path_str.split("/")

    # Handle /home/<username>/workspace/...
    if len(parts) >= 4 and parts[1] == "home" and "workspace" in parts:
        username = parts[2]
        workspace_idx = parts.index("workspace")
        relative = "/".join(parts[workspace_idx + 1:])

        try:
            from hermes_cli.profiles import list_profiles, get_profile_dir

            # Direct match: profile name contains the username
            for profile_name in list_profiles():
                if username in profile_name:
                    host_workspace = get_profile_dir(profile_name) / "workspace" / relative
                    if host_workspace.is_file():
                        return str(host_workspace)

            # Fallback: try using username directly as profile name
            try:
                host_workspace = get_profile_dir(username) / "workspace" / relative
                if host_workspace.is_file():
                    return str(host_workspace)
            except Exception:
                pass
        except Exception:
            pass

    # Also try: the path might be relative to current profile's workspace
    try:
        from hermes_constants import get_hermes_home
        hermes_home = get_hermes_home()
        # Check if file is under current profile's workspace
        ws = hermes_home / "workspace" / Path(container_path).name
        if ws.is_file():
            return str(ws)
    except Exception:
        pass

    return None


SEND_FILE_SCHEMA = {
    "name": "send_file",
    "description": "Send a file from your workspace to the user as a native attachment (document upload). Use this when the user asks you to send/share/deliver a file.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file in your workspace, e.g. /home/<username>/workspace/report.pdf",
            },
        },
        "required": ["file_path"],
    },
}

registry.register(
    name="send_file",
    toolset="messaging",
    schema=SEND_FILE_SCHEMA,
    handler=lambda args, **kw: send_file_tool(
        file_path=args.get("file_path", ""),
        task_id=kw.get("task_id"),
        session_id=kw.get("session_id"),
    ),
    check_fn=_check_send_file_requirements,
)
