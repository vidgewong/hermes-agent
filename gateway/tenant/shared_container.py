"""Shared tenant container — single container with per-user Linux isolation.

One long-lived container serves all tenants. Each tenant gets:
- A Linux user (uid from DB)
- A home dir at /home/<username>/workspace/ (bind-mounted from profile)
- Commands dispatched via `docker exec --user <uid>:<uid> -w /home/<username>/workspace`

New tenants trigger a container rebuild to pick up new volume mounts.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gateway.tenant.registry import UserRegistry

logger = logging.getLogger(__name__)

CONTAINER_NAME = "hermes-tenant-shared"
CONTAINER_IMAGE = "hermes-tenant:latest"
_UID_BASE = 2000  # Start allocating UIDs from here

_lock = threading.Lock()
_container_running = False


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/usr/bin/docker", *args],
        capture_output=True, text=True, check=check, timeout=30,
    )


def allocate_uid(user_index: int) -> int:
    """Allocate a stable UID for a tenant. Index is 0-based user creation order."""
    return _UID_BASE + user_index


def is_container_running() -> bool:
    """Check if the shared tenant container is currently running."""
    try:
        result = _docker("inspect", "-f", "{{.State.Running}}", CONTAINER_NAME, check=False)
        return result.stdout.strip() == "true"
    except Exception:
        return False


def get_volume_mounts(registry_users: list) -> list[str]:
    """Build -v arguments for all registered tenants.

    Each user gets their profile workspace mounted at /home/<username>/workspace.
    """
    from hermes_cli.profiles import get_profile_dir

    volumes = []
    for user in registry_users:
        profile_name = None
        for p in (user.profiles or []):
            if p.is_primary:
                profile_name = p.profile_name
                break
        if not profile_name:
            continue

        profile_dir = get_profile_dir(profile_name)
        workspace_dir = profile_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        home_path = f"/home/{user.username}"
        volumes.extend(["-v", f"{workspace_dir}:{home_path}/workspace:rw"])

    return volumes


def start_or_rebuild(registry_users: list) -> bool:
    """Start the shared container, or rebuild it with updated mounts.

    Returns True if container is running after this call.
    """
    global _container_running

    with _lock:
        # Stop existing if running
        if is_container_running():
            _docker("stop", CONTAINER_NAME, check=False)

        # Remove old container
        _docker("rm", "-f", CONTAINER_NAME, check=False)

        # Build volume args
        vol_args = get_volume_mounts(registry_users)

        # Network proxy env vars for corporate environment
        _PROXY = "http://shrdcm025.cnrd.corpintra.net:3128/"
        _NO_PROXY = (
            "wiki.swf.i.mercedes-benz.com,issue.swf.i.mercedes-benz.com,"
            "artifact.swfcn.i.mercedes-benz.com,git.swfcn.i.mercedes-benz.com,"
            "artifact-swfcn-lsh.cn133.corpintra.net,artifact-swfcn-sh.cnrd.corpintra.net,"
            "s133it4ada020.cn133.corpintra.net,stccit4ada020.cnrd.corpintra.net,"
            "shrdcm040.cnrd.corpintra.net,shrdcm007.cnrd.corpintra.net,"
            "git.swf.i.mercedes-benz.com,artifact.swf.i.mercedes-benz.com,"
            "artifacts.swf.i.mercedes-benz.com,git.swf.daimler.com,"
            "53.127.126.11,localhost,127.0.0.1,10.*,192.168.*,53.*"
        )

        # Build run command. Override entrypoint to sleep infinity
        # regardless of what the image has (avoids stale ENTRYPOINT issues).
        cmd = [
            "run", "-d",
            "--name", CONTAINER_NAME,
            "--label", "hermes-tenant-managed=1",
            "--label", "hermes-tenant-shared=1",
            "--cap-drop", "ALL",
            "--cap-add", "DAC_OVERRIDE",
            "--cap-add", "CHOWN",
            "--cap-add", "FOWNER",
            "--cap-add", "SETUID",
            "--cap-add", "SETGID",
            "--security-opt", "no-new-privileges",
            "--network", "host",
            "--entrypoint", "sleep",
            "-e", f"http_proxy={_PROXY}",
            "-e", f"https_proxy={_PROXY}",
            "-e", f"HTTP_PROXY={_PROXY}",
            "-e", f"HTTPS_PROXY={_PROXY}",
            "-e", f"no_proxy={_NO_PROXY}",
            "-e", f"NO_PROXY={_NO_PROXY}",
            *vol_args,
            CONTAINER_IMAGE,
            "infinity",
        ]

        try:
            _docker(*cmd)
            _container_running = True
            logger.info("Shared tenant container started with %d user mount(s)", len(vol_args) // 2)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to start shared tenant container: %s", e.stderr)
            _container_running = False
            return False

        # Ensure home dirs exist and are locked down inside the container.
        # We don't need /etc/passwd entries — docker exec --user uid:uid works
        # with bare UIDs. Only need the directory structure + permissions.
        for user in registry_users:
            uid = user.container_uid
            if uid is None:
                continue
            username = user.username
            try:
                _docker(
                    "exec", CONTAINER_NAME,
                    "sh", "-c",
                    f"mkdir -p /home/{username}/workspace && "
                    f"chown -R {uid}:{uid} /home/{username} && "
                    f"chmod 700 /home/{username}",
                    check=False,
                )
            except Exception as exc:
                logger.warning("Failed to setup home for %s in container: %s", username, exc)

        return True


def ensure_running(registry_users: list) -> bool:
    """Ensure the shared container is running. Start if not."""
    if is_container_running():
        return True
    return start_or_rebuild(registry_users)


def add_user_to_running_container(username: str, uid: int) -> bool:
    """Add a new user to an already-running container (without restart).

    Note: volume mounts cannot be added to a running container.
    A restart is needed for the new user's workspace mount.
    """
    if not is_container_running():
        return False

    try:
        _docker(
            "exec", CONTAINER_NAME,
            "sh", "-c",
            f"addgroup --gid {uid} {username} 2>/dev/null; "
            f"adduser --uid {uid} --gid {uid} --disabled-password "
            f"--gecos '' --home /home/{username} {username} 2>/dev/null; "
            f"mkdir -p /home/{username}/workspace && "
            f"chown {uid}:{uid} /home/{username} /home/{username}/workspace && "
            f"chmod 700 /home/{username}",
            check=False,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to add user %s to running container: %s", username, exc)
        return False


def exec_as_user(username: str, uid: int, command: str, workdir: str | None = None) -> tuple[str, int]:
    """Execute a command in the shared container as a specific user.

    Returns (output, exit_code).
    """
    cwd = workdir or f"/home/{username}/workspace"
    try:
        result = _docker(
            "exec",
            "--user", f"{uid}:{uid}",
            "-w", cwd,
            CONTAINER_NAME,
            "bash", "-c", command,
            check=False,
        )
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", 124
    except Exception as exc:
        return f"Exec failed: {exc}", 1


def stop_container() -> None:
    """Stop the shared container."""
    global _container_running
    with _lock:
        _docker("stop", CONTAINER_NAME, check=False)
        _container_running = False
