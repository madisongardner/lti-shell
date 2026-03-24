"""Container lifecycle helpers for assignment attempts."""

import os

import docker
from docker.errors import DockerException, NotFound
from sqlalchemy import false

# Runtime defaults (can be overridden with environment variables).
DEFAULT_IMAGE = os.getenv("LTI_SHELL_IMAGE", "ubuntu:24.04")
DEFAULT_CPU_NANOS = int(os.getenv("LTI_SHELL_CPU_NANOS", "500000000"))
DEFAULT_MEM_LIMIT = os.getenv("LTI_SHELL_MEM_LIMIT", "256m")
DEFAULT_USER = os.getenv("LTI_SHELL_CONTAINER_USER", "65534:65534")


def _client():
    """Return a live Docker client, or raise a clear runtime error."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException as exc:
        raise RuntimeError(f"Docker unavailable: {exc}") from exc


def create_attempt_container():
    """Start a fresh locked-down sandbox container for an attempt."""
    client = _client()
    container = client.containers.run(
        image=DEFAULT_IMAGE,
        command=["/bin/bash", "-lc", "sleep infinity"],  # Keep shell alive for terminal attach.
        detach=True,
        stdin_open=True,
        tty=True,
        network_disabled=True,  # No outbound/inbound network access from sandbox.
        user=DEFAULT_USER,  # Run as non-root.
        cap_drop=["ALL"],  # Drop Linux capabilities.
        security_opt=["no-new-privileges:true"],  # Prevent privilege escalation.
        mem_limit=DEFAULT_MEM_LIMIT,  # Hard memory cap.
        nano_cpus=DEFAULT_CPU_NANOS,  # Hard CPU cap.
        pids_limit=128,  # Prevent fork bombs.
        # read_only= false,  # Immutable base filesystem.
        tmpfs={
            "/tmp": "rw,noexec,nosuid,size=64m",
            "/workspace": "rw,noexec,nosuid,size=128m",
        },
        auto_remove=True,  # Remove container after stop.
    )
    return {"container_id": container.id, "docker_status": container.status}


def reset_attempt_container(container_id: str | None):
    """Terminate existing attempt container (if any), then start a new one."""
    terminate_attempt_container(container_id)
    return create_attempt_container()


def terminate_attempt_container(container_id: str | None):
    """Stop an attempt container if present; return whether it was stopped."""
    if not container_id:
        return False

    client = _client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=3)
        return True
    except NotFound:
        return False


def get_container_status(container_id: str | None):
    """Return current runtime status for a container id."""
    if not container_id:
        return {"docker_status": "none"}

    client = _client()
    try:
        container = client.containers.get(container_id)
        container.reload()
        return {"docker_status": container.status, "container_id": container.id}
    except NotFound:
        return {"docker_status": "not_found", "container_id": container_id}
