"""Tenant Docker environment — per-profile container lifecycle management.

Provides TenantDockerEnvironment, a configuration helper that manages
Docker containers as isolated exec targets for multi-tenant operation.
The agent runs on the HOST; only file/terminal tool calls are dispatched
into the container via `docker exec`.

Container lifecycle:
  - Containers use the `sleep infinity` pattern (pure exec target, not a service).
  - A container stays alive between turns; idle timeout handles cleanup.
  - Container reuse is keyed by (username, profile_name) labels.

Mount layout:
  Host path                                  Container path       Mode
  ─────────────────────────────────────────  ───────────────────  ────
  ~/.hermes/profiles/<name>/workspace/       /workspace           rw
  ~/.hermes/profiles/<name>/skills/          /skills              ro
  ~/.hermes/profiles/<name>/memories/        /memories            rw
  ~/.hermes/profiles/<name>/.claude/         /home/agent/.claude  ro
  <hermes-agent repo>/                       /opt/hermes-agent    ro
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default idle timeout: 30 minutes of inactivity before a container is stopped.
_DEFAULT_IDLE_TIMEOUT_SECONDS = 1800

# Docker label keys for tenant containers.
_LABEL_TENANT = "hermes-tenant"
_LABEL_PROFILE = "hermes-profile"
_LABEL_MANAGED = "hermes-tenant-managed"


def _find_docker() -> str:
    """Locate docker executable, reusing the core docker environment's finder."""
    try:
        from tools.environments.docker import find_docker
        exe = find_docker()
        if exe:
            return exe
    except ImportError:
        pass
    # Fallback: assume docker is on PATH.
    return "docker"


def _get_profile_dir(profile_name: str) -> Path:
    """Resolve a profile name to its HERMES_HOME directory."""
    try:
        from hermes_cli.profiles import get_profile_dir
        return get_profile_dir(profile_name)
    except ImportError:
        # Fallback for environments where hermes_cli is not importable.
        from pathlib import Path as _Path
        home = _Path.home() / ".hermes"
        if profile_name == "default":
            return home
        return home / "profiles" / profile_name


def _get_hermes_agent_root() -> Path:
    """Return the path to the hermes-agent codebase on the host."""
    # The codebase root is the parent of the gateway/ directory.
    return Path(__file__).resolve().parent.parent.parent


class TenantDockerEnvironment:
    """Manages a per-tenant Docker container as an exec target.

    This is NOT a subclass of DockerEnvironment/BaseEnvironment. It is a
    lifecycle manager that creates/finds containers with the correct mounts
    and labels, then provides a `docker_exec_prefix()` method that callers
    use to run commands inside the container.

    Usage:
        env = TenantDockerEnvironment(
            username="alice",
            profile_name="alice_profile",
            image="hermes-tenant:latest",
        )
        env.ensure_running()
        # Then use env.container_id with `docker exec` for command dispatch.
    """

    def __init__(
        self,
        username: str,
        profile_name: str,
        image: str = "hermes-tenant:latest",
        idle_timeout: int = _DEFAULT_IDLE_TIMEOUT_SECONDS,
        network: bool = True,
        extra_mounts: list[str] | None = None,
    ):
        self._username = username
        self._profile_name = profile_name
        self._image = image
        self._idle_timeout = idle_timeout
        self._network = network
        self._extra_mounts = extra_mounts or []
        self._docker_exe = _find_docker()
        self._container_id: Optional[str] = None
        self._last_activity: float = time.monotonic()

    @property
    def username(self) -> str:
        return self._username

    @property
    def profile_name(self) -> str:
        return self._profile_name

    @property
    def container_id(self) -> Optional[str]:
        return self._container_id

    @property
    def last_activity(self) -> float:
        """Monotonic timestamp of last recorded activity."""
        return self._last_activity

    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.monotonic() - self._last_activity

    @property
    def is_idle_expired(self) -> bool:
        """True if the container has been idle longer than the timeout."""
        return self.idle_seconds > self._idle_timeout

    def touch_activity(self) -> None:
        """Record that the container was just used."""
        self._last_activity = time.monotonic()

    # ------------------------------------------------------------------
    # Mount configuration
    # ------------------------------------------------------------------

    def _build_volume_args(self) -> list[str]:
        """Build -v arguments for the container's bind mounts."""
        profile_dir = _get_profile_dir(self._profile_name)
        hermes_root = _get_hermes_agent_root()

        # Ensure required profile subdirectories exist on the host.
        workspace_dir = profile_dir / "workspace"
        skills_dir = profile_dir / "skills"
        memories_dir = profile_dir / "memories"
        claude_dir = profile_dir / ".claude"

        workspace_dir.mkdir(parents=True, exist_ok=True)
        memories_dir.mkdir(parents=True, exist_ok=True)

        volume_args = []

        # Workspace: read-write — agent's working directory.
        volume_args.extend(["-v", f"{workspace_dir}:/workspace:rw"])

        # Skills: read-only — agent can read skill definitions.
        if skills_dir.is_dir():
            volume_args.extend(["-v", f"{skills_dir}:/skills:ro"])

        # Memories: read-write — agent's persistent memory store.
        volume_args.extend(["-v", f"{memories_dir}:/memories:rw"])

        # .claude config: read-only — agent config (CLAUDE.md, etc.).
        if claude_dir.is_dir():
            volume_args.extend(["-v", f"{claude_dir}:/home/agent/.claude:ro"])

        # Hermes agent codebase: read-only — runtime code.
        volume_args.extend(["-v", f"{hermes_root}:/opt/hermes-agent:ro"])

        # Extra user-configured mounts.
        for mount in self._extra_mounts:
            if isinstance(mount, str) and ":" in mount:
                volume_args.extend(["-v", mount])

        return volume_args

    # ------------------------------------------------------------------
    # Label configuration
    # ------------------------------------------------------------------

    def _build_label_args(self) -> list[str]:
        """Build --label arguments for container identification."""
        return [
            "--label", f"{_LABEL_MANAGED}=1",
            "--label", f"{_LABEL_TENANT}={self._username}",
            "--label", f"{_LABEL_PROFILE}={self._profile_name}",
        ]

    # ------------------------------------------------------------------
    # Container lookup by labels
    # ------------------------------------------------------------------

    def _find_existing_container(self) -> Optional[tuple[str, str]]:
        """Find a container matching this tenant's labels.

        Returns (container_id, state) if found, None otherwise.
        State is one of: running, exited, created, paused, etc.
        """
        try:
            result = subprocess.run(
                [
                    self._docker_exe, "ps", "-a",
                    "--filter", f"label={_LABEL_MANAGED}=1",
                    "--filter", f"label={_LABEL_TENANT}={self._username}",
                    "--filter", f"label={_LABEL_PROFILE}={self._profile_name}",
                    "--format", "{{.ID}}\t{{.State}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Tenant container lookup failed: %s", e)
            return None

        if result.returncode != 0:
            logger.debug(
                "Tenant container lookup returned %d: %s",
                result.returncode, result.stderr.strip(),
            )
            return None

        lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        if not lines:
            return None

        # Prefer a running container if multiple exist.
        running = None
        first = None
        for ln in lines:
            parts = ln.split("\t", 1)
            if len(parts) != 2:
                continue
            cid, state = parts[0], parts[1].lower()
            if first is None:
                first = (cid, state)
            if state == "running" and running is None:
                running = (cid, state)

        return running or first

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    def ensure_running(self) -> str:
        """Ensure the tenant container is running, creating or starting as needed.

        Returns the container ID.
        """
        # Check if we already have a tracked container that is running.
        if self._container_id:
            if self._is_container_running(self._container_id):
                self.touch_activity()
                return self._container_id
            # Container stopped/removed — clear the reference.
            self._container_id = None

        # Look for an existing container by labels.
        existing = self._find_existing_container()
        if existing is not None:
            cid, state = existing
            if state == "running":
                self._container_id = cid
                self.touch_activity()
                logger.info(
                    "Tenant %s/%s: reusing running container %s",
                    self._username, self._profile_name, cid[:12],
                )
                return cid
            # Container exists but is stopped — restart it.
            try:
                subprocess.run(
                    [self._docker_exe, "start", cid],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                    stdin=subprocess.DEVNULL,
                )
                self._container_id = cid
                self.touch_activity()
                logger.info(
                    "Tenant %s/%s: restarted stopped container %s",
                    self._username, self._profile_name, cid[:12],
                )
                return cid
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                logger.warning(
                    "Tenant %s/%s: failed to restart container %s: %s — creating new",
                    self._username, self._profile_name, cid[:12], e,
                )
                # Remove the broken container before creating a new one.
                self._remove_container(cid)

        # No reusable container found — create a new one.
        return self._create_container()

    def _create_container(self) -> str:
        """Create and start a new tenant container."""
        container_name = f"hermes-tenant-{self._username}-{uuid.uuid4().hex[:6]}"
        volume_args = self._build_volume_args()
        label_args = self._build_label_args()

        network_args = [] if self._network else ["--network=none"]

        run_cmd = [
            self._docker_exe, "run", "-d",
            "--init",
            "--name", container_name,
            *label_args,
            *network_args,
            "-w", "/workspace",
            *volume_args,
            self._image,
            # Entrypoint is already `sleep infinity` in the Dockerfile,
            # but we specify it explicitly for robustness.
            "sleep", "infinity",
        ]

        logger.debug("Tenant container create: %s", " ".join(run_cmd))

        try:
            result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
                stdin=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(
                "Tenant %s/%s: failed to create container: %s",
                self._username, self._profile_name, e,
            )
            # Cleanup orphaned container on failure.
            subprocess.run(
                [self._docker_exe, "rm", "-f", container_name],
                capture_output=True, timeout=10,
                stdin=subprocess.DEVNULL,
            )
            raise RuntimeError(
                f"Failed to create tenant container for {self._username}/{self._profile_name}"
            ) from e

        self._container_id = result.stdout.strip()
        self.touch_activity()
        logger.info(
            "Tenant %s/%s: created container %s (%s)",
            self._username, self._profile_name,
            container_name, self._container_id[:12],
        )
        return self._container_id

    def _is_container_running(self, container_id: str) -> bool:
        """Check if a container is currently running."""
        try:
            result = subprocess.run(
                [
                    self._docker_exe, "inspect",
                    "--format", "{{.State.Running}}",
                    container_id,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                stdin=subprocess.DEVNULL,
            )
            return result.returncode == 0 and result.stdout.strip().lower() == "true"
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _remove_container(self, container_id: str) -> None:
        """Force-remove a container, ignoring errors."""
        try:
            subprocess.run(
                [self._docker_exe, "rm", "-f", container_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Failed to remove container %s: %s", container_id[:12], e)

    # ------------------------------------------------------------------
    # Command dispatch helper
    # ------------------------------------------------------------------

    def docker_exec_prefix(self, workdir: str = "/workspace") -> list[str]:
        """Return the `docker exec` prefix for dispatching commands.

        Callers append their command to this list:
            prefix = env.docker_exec_prefix()
            subprocess.run([*prefix, "bash", "-c", user_command])
        """
        if not self._container_id:
            raise RuntimeError("Container not running — call ensure_running() first")
        self.touch_activity()
        return [self._docker_exe, "exec", "-w", workdir, self._container_id]

    # ------------------------------------------------------------------
    # Idle timeout management
    # ------------------------------------------------------------------

    def stop_if_idle(self) -> bool:
        """Stop the container if it has been idle longer than the timeout.

        Returns True if the container was stopped, False otherwise.
        """
        if not self._container_id:
            return False

        if not self.is_idle_expired:
            return False

        logger.info(
            "Tenant %s/%s: container %s idle for %.0fs (timeout=%ds) — stopping",
            self._username, self._profile_name,
            self._container_id[:12],
            self.idle_seconds,
            self._idle_timeout,
        )
        self.stop()
        return True

    def stop(self) -> None:
        """Stop the container gracefully."""
        if not self._container_id:
            return
        try:
            subprocess.run(
                [self._docker_exe, "stop", "-t", "10", self._container_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                stdin=subprocess.DEVNULL,
            )
            logger.info(
                "Tenant %s/%s: stopped container %s",
                self._username, self._profile_name, self._container_id[:12],
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning(
                "Tenant %s/%s: failed to stop container %s: %s",
                self._username, self._profile_name,
                self._container_id[:12], e,
            )
        self._container_id = None

    def destroy(self) -> None:
        """Force-remove the container entirely."""
        if not self._container_id:
            return
        self._remove_container(self._container_id)
        logger.info(
            "Tenant %s/%s: destroyed container %s",
            self._username, self._profile_name, self._container_id[:12],
        )
        self._container_id = None

    # ------------------------------------------------------------------
    # Class-level utilities for fleet management
    # ------------------------------------------------------------------

    @classmethod
    def find_all_tenant_containers(cls) -> list[dict]:
        """Find all managed tenant containers.

        Returns a list of dicts with keys: id, state, username, profile.
        """
        docker_exe = _find_docker()
        try:
            result = subprocess.run(
                [
                    docker_exe, "ps", "-a",
                    "--filter", f"label={_LABEL_MANAGED}=1",
                    "--format", '{{.ID}}\t{{.State}}\t{{.Label "hermes-tenant"}}\t{{.Label "hermes-profile"}}',
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Failed to list tenant containers: %s", e)
            return []

        if result.returncode != 0:
            return []

        containers = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                containers.append({
                    "id": parts[0],
                    "state": parts[1],
                    "username": parts[2],
                    "profile": parts[3],
                })
        return containers

    @classmethod
    def stop_idle_containers(cls, timeout_seconds: int = _DEFAULT_IDLE_TIMEOUT_SECONDS) -> int:
        """Stop all tenant containers that have been idle beyond the timeout.

        This is a fleet-level operation that checks container start/activity time
        using `docker inspect`. Returns the number of containers stopped.

        Note: This uses container-level inspection since we cannot track
        per-container monotonic activity timestamps across processes. In practice,
        the TenantContainerPool (below) tracks activity for in-process containers.
        """
        docker_exe = _find_docker()
        containers = cls.find_all_tenant_containers()
        stopped = 0

        for info in containers:
            if info["state"] != "running":
                continue
            # Check how long the container has been running without recent exec.
            # We use the container's last-started time as a proxy when no
            # in-process activity tracker is available.
            if _container_idle_beyond(docker_exe, info["id"], timeout_seconds):
                try:
                    subprocess.run(
                        [docker_exe, "stop", "-t", "10", info["id"]],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                        stdin=subprocess.DEVNULL,
                    )
                    stopped += 1
                    logger.info(
                        "Stopped idle tenant container %s (user=%s, profile=%s)",
                        info["id"][:12], info["username"], info["profile"],
                    )
                except (subprocess.TimeoutExpired, OSError) as e:
                    logger.debug("Failed to stop container %s: %s", info["id"][:12], e)

        return stopped


def _container_idle_beyond(docker_exe: str, container_id: str, timeout_seconds: int) -> bool:
    """Check if a container's last activity was beyond the timeout threshold.

    Uses `docker inspect` to get the container's StartedAt time as a baseline.
    This is a conservative estimate — a container that was recently exec'd into
    may still appear idle by this metric if the only tracker is StartedAt.
    For accurate per-container tracking, use TenantContainerPool.
    """
    import datetime

    try:
        result = subprocess.run(
            [docker_exe, "inspect", "--format", "{{.State.StartedAt}}", container_id],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False

    if result.returncode != 0:
        return False

    raw = result.stdout.strip()
    if not raw or raw.startswith("0001-01-01"):
        return False

    # Parse the timestamp (Docker uses RFC3339 with nanoseconds).
    import re
    raw = re.sub(r"(\.\d{6})\d+", r"\1", raw)
    raw = raw.replace("Z", "+00:00")
    try:
        started_at = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return False

    now = datetime.datetime.now(datetime.timezone.utc)
    age = (now - started_at).total_seconds()
    return age > timeout_seconds


class TenantContainerPool:
    """In-process pool of TenantDockerEnvironment instances.

    Provides container reuse across multiple agent sessions within the same
    gateway process. Keyed by (username, profile_name).
    """

    def __init__(
        self,
        image: str = "hermes-tenant:latest",
        idle_timeout: int = _DEFAULT_IDLE_TIMEOUT_SECONDS,
        network: bool = True,
    ):
        self._image = image
        self._idle_timeout = idle_timeout
        self._network = network
        self._pool: dict[tuple[str, str], TenantDockerEnvironment] = {}

    def get_or_create(
        self,
        username: str,
        profile_name: str,
        extra_mounts: list[str] | None = None,
    ) -> TenantDockerEnvironment:
        """Get an existing environment or create a new one for this tenant."""
        key = (username, profile_name)

        if key in self._pool:
            env = self._pool[key]
            env.ensure_running()
            return env

        env = TenantDockerEnvironment(
            username=username,
            profile_name=profile_name,
            image=self._image,
            idle_timeout=self._idle_timeout,
            network=self._network,
            extra_mounts=extra_mounts,
        )
        env.ensure_running()
        self._pool[key] = env
        return env

    def reap_idle(self) -> int:
        """Stop idle containers and remove them from the pool.

        Returns the number of containers stopped.
        """
        stopped = 0
        to_remove = []

        for key, env in self._pool.items():
            if env.stop_if_idle():
                to_remove.append(key)
                stopped += 1

        for key in to_remove:
            del self._pool[key]

        return stopped

    def stop_all(self) -> None:
        """Stop all containers in the pool."""
        for env in self._pool.values():
            env.stop()
        self._pool.clear()

    def destroy_all(self) -> None:
        """Force-remove all containers in the pool."""
        for env in self._pool.values():
            env.destroy()
        self._pool.clear()

    @property
    def active_count(self) -> int:
        """Number of environments tracked in the pool."""
        return len(self._pool)

    def get_status(self) -> list[dict]:
        """Return status information for all pooled environments."""
        statuses = []
        for (username, profile_name), env in self._pool.items():
            statuses.append({
                "username": username,
                "profile_name": profile_name,
                "container_id": env.container_id,
                "idle_seconds": round(env.idle_seconds, 1),
                "idle_expired": env.is_idle_expired,
            })
        return statuses
