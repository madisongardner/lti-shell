"""Container lifecycle helpers for assignment attempts."""

import io
import os
import subprocess
import tarfile
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound, NotFound

# Runtime defaults (can be overridden with environment variables).
DEFAULT_IMAGE = os.getenv("LTI_SHELL_IMAGE", "lti-shell-sandbox:latest")
DEFAULT_CPU_NANOS = int(os.getenv("LTI_SHELL_CPU_NANOS", "500000000"))
DEFAULT_MEM_LIMIT = os.getenv("LTI_SHELL_MEM_LIMIT", "256m")
DEFAULT_USER = os.getenv("LTI_SHELL_CONTAINER_USER", "65532:65532")
DEFAULT_HOME = os.getenv("LTI_SHELL_CONTAINER_HOME", "/home/sandbox")
DEFAULT_LANG = os.getenv("LTI_SHELL_LANG", "C.UTF-8")
DEFAULT_TERM = os.getenv("LTI_SHELL_TERM", "xterm-256color")
DEFAULT_TMP_SIZE = os.getenv("LTI_SHELL_TMP_SIZE", "64m")
DEFAULT_WORKSPACE_SIZE = os.getenv("LTI_SHELL_WORKSPACE_SIZE", "256m")


def _user_ids(user_spec: str) -> tuple[int, int]:
    """Parse uid/gid from Docker user spec (uid[:gid])."""
    parts = (user_spec or "").split(":")
    uid_text = (parts[0] if parts and parts[0] else "65532").strip()
    gid_text = (parts[1] if len(parts) > 1 and parts[1] else uid_text).strip()
    try:
        return int(uid_text), int(gid_text)
    except ValueError:
        return 65532, 65532


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
    uid, gid = _user_ids(DEFAULT_USER)
    try:
        container = client.containers.run(
            image=DEFAULT_IMAGE,
            command=["/bin/bash", "-lc", "sleep infinity"],  # Keep shell alive for terminal attach.
            detach=True,
            stdin_open=True,
            tty=True,
            network_disabled=True,  # No outbound/inbound network access from sandbox.
            user=DEFAULT_USER,  # Run as non-root.
            working_dir="/workspace",
            environment={
                "HOME": DEFAULT_HOME,
                "LANG": DEFAULT_LANG,
                "TERM": DEFAULT_TERM,
            },
            cap_drop=["ALL"],  # Drop Linux capabilities.
            security_opt=["no-new-privileges:true"],  # Prevent privilege escalation.
            mem_limit=DEFAULT_MEM_LIMIT,  # Hard memory cap.
            nano_cpus=DEFAULT_CPU_NANOS,  # Hard CPU cap.
            pids_limit=128,  # Prevent fork bombs.
            # read_only= false,  # Immutable base filesystem.
            tmpfs={
                "/tmp": f"rw,noexec,nosuid,size={DEFAULT_TMP_SIZE},mode=1777",
                # Ensure active container user can write assignment files.
                "/workspace": f"rw,exec,nosuid,size={DEFAULT_WORKSPACE_SIZE},uid={uid},gid={gid},mode=770",
            },
            auto_remove=True,  # Remove container after stop.
        )
    except ImageNotFound as exc:
        raise RuntimeError(
            "Sandbox image not found. Build it with "
            "'docker build -t lti-shell-sandbox:latest -f docker/sandbox/Dockerfile .' "
            "or set LTI_SHELL_IMAGE to an existing image."
        ) from exc

    return {"container_id": container.id, "docker_status": container.status}


def _build_dir_tar_bytes(source_dir: Path, uid: int, gid: int) -> tuple[bytes, int]:
    """Pack source_dir contents into tar bytes with normalized ownership."""
    buffer = io.BytesIO()
    file_count = 0

    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for path in sorted(source_dir.rglob("*")):
            rel_path = path.relative_to(source_dir)

            def _normalize(info: tarfile.TarInfo) -> tarfile.TarInfo:
                info.uid = uid
                info.gid = gid
                info.uname = ""
                info.gname = ""
                return info

            tar.add(path, arcname=str(rel_path), recursive=False, filter=_normalize)
            if path.is_file():
                file_count += 1

    buffer.seek(0)
    return buffer.getvalue(), file_count


def populate_workspace_from_starter(container_id: str | None, starter_extracted_path: str | None):
    """Copy starter files into /workspace for a running attempt container."""
    if not container_id:
        raise ValueError("Attempt has no active container")
    if not starter_extracted_path:
        return {"copied": False, "file_count": 0}

    source_dir = Path(starter_extracted_path)
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError("Starter artifact directory is missing")

    client = _client()
    try:
        container = client.containers.get(container_id)
    except NotFound as exc:
        raise ValueError("Attempt container not found") from exc

    uid, gid = _user_ids(DEFAULT_USER)
    archive_bytes, file_count = _build_dir_tar_bytes(source_dir, uid=uid, gid=gid)
    process = subprocess.run(
        ["docker", "exec", "-i", container.id, "tar", "-xmf", "-", "-C", "/workspace"],
        input=archive_bytes,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", "ignore").strip()
        raise RuntimeError(f"Unable to copy starter files into container workspace: {stderr}")

    return {"copied": True, "file_count": file_count}


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
