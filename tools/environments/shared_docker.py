"""Shared Docker environment — dispatches commands via docker exec on a pre-existing container.

Unlike DockerEnvironment which manages its own container lifecycle, this
environment assumes a long-running shared container (hermes-tenant-shared)
and executes commands as a specific Linux user via --user.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)


class SharedDockerEnvironment:
    """Execute commands in a shared container as a specific user."""

    def __init__(
        self,
        container_name: str,
        uid: int,
        username: str,
        cwd: str = "/workspace",
        timeout: int = 180,
    ):
        self.container_name = container_name
        self.uid = uid
        self.username = username
        self.cwd = cwd
        self.timeout = timeout
        self._session_id: Optional[str] = None

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        workdir: Optional[str] = None,
        cwd: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Execute a command in the shared container as the tenant user."""
        effective_timeout = timeout or self.timeout
        effective_cwd = cwd or workdir or self.cwd

        cmd = [
            "/usr/bin/docker", "exec",
            "--user", f"{self.uid}:{self.uid}",
            "-w", effective_cwd,
            "-e", f"HOME=/home/{self.username}",
            "-e", f"USER={self.username}",
            self.container_name,
            "bash", "-c", command,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            output = result.stdout
            if result.stderr:
                output = output + result.stderr if output else result.stderr
            return {
                "output": output,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "output": f"Command timed out after {effective_timeout}s",
                "exit_code": 124,
            }
        except Exception as exc:
            return {
                "output": f"Execution failed: {exc}",
                "exit_code": 1,
            }

    def cleanup(self):
        """No-op — the shared container is managed externally."""
        pass

    def __repr__(self) -> str:
        return (
            f"SharedDockerEnvironment(container={self.container_name}, "
            f"user={self.username}({self.uid}), cwd={self.cwd})"
        )
