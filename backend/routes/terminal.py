import json
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import docker
from docker.errors import DockerException, NotFound
from flask import request, session

from database import SessionLocal
from models.attempt import Attempt
from services.attempt_cleanup_service import touch_attempt_activity


@contextmanager
def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ws_error(ws, message: str):
    try:
        ws.send(json.dumps({"type": "error", "message": message}))
    except Exception:
        # Socket may already be closed; avoid raising from error handling.
        pass


def _require_user():
    user = session.get("user")
    if not user:
        raise PermissionError("Not authenticated")
    return user


def _can_access_attempt(user: dict, attempt: Attempt) -> bool:
    if user.get("role") == "teacher":
        return attempt.resource_link_id == user.get("resource_link_id")
    return (
        attempt.user_sub == user.get("sub")
        and attempt.resource_link_id == user.get("resource_link_id")
    )


def _get_attempt_for_user(attempt_id: str):
    user = _require_user()
    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            raise ValueError("Attempt not found")
        if not _can_access_attempt(user, attempt):
            raise PermissionError("Forbidden")
        return attempt


def _docker_client():
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException as exc:
        raise RuntimeError(f"Docker daemon unavailable: {exc}") from exc


def register_terminal_socket(sock):
    @sock.route("/ws/terminal")
    def terminal_socket(ws):
        """
        WebSocket bridge for xterm.js <-> docker exec bash.
        Query param required: attempt_id
        """
        try:
            attempt_id = request.args.get("attempt_id")
            if not attempt_id:
                raise ValueError("Missing attempt_id")

            attempt = _get_attempt_for_user(attempt_id)
            if not attempt.container_id:
                raise ValueError("Attempt has no active container")

            touch_interval = timedelta(seconds=10)
            touch_lock = threading.Lock()
            last_touch_at = datetime.now(timezone.utc)

            def maybe_touch(force=False):
                nonlocal last_touch_at
                now = datetime.now(timezone.utc)
                with touch_lock:
                    if not force and (now - last_touch_at) < touch_interval:
                        return
                    try:
                        touch_attempt_activity(attempt_id, now=now)
                    except Exception:
                        # Terminal I/O should continue even if activity touch fails.
                        pass
                    last_touch_at = now

            maybe_touch(force=True)

            client = _docker_client()
            try:
                container = client.containers.get(attempt.container_id)
            except NotFound:
                _ws_error(ws, "Container not found")
                return

            exec_info = client.api.exec_create(
                container.id,
                cmd=["/bin/bash"],
                stdin=True,
                stdout=True,
                stderr=True,
                tty=True,
            )
            exec_id = exec_info["Id"]

            docker_socket = client.api.exec_start(exec_id, tty=True, stream=False, socket=True)
            raw_socket = getattr(docker_socket, "_sock", docker_socket)
            raw_socket.settimeout(0.2)

            stop_event = threading.Event()
            send_lock = threading.Lock()

            def safe_send(payload):
                with send_lock:
                    ws.send(json.dumps(payload))

            def stream_docker_output():
                while not stop_event.is_set():
                    try:
                        chunk = raw_socket.recv(4096)
                        if not chunk:
                            break
                        maybe_touch()
                        safe_send({"type": "output", "data": chunk.decode("utf-8", "ignore")})
                    except OSError:
                        continue
                    except Exception:
                        break

            output_thread = threading.Thread(target=stream_docker_output, daemon=True)
            output_thread.start()

            try:
                while True:
                    msg = ws.receive()
                    if msg is None:
                        break

                    try:
                        payload = json.loads(msg)
                    except json.JSONDecodeError:
                        payload = {"type": "input", "data": msg}

                    msg_type = payload.get("type")

                    if msg_type == "input":
                        maybe_touch()
                        raw_socket.send((payload.get("data") or "").encode("utf-8", "ignore"))

                    elif msg_type == "resize":
                        maybe_touch()
                        cols = int(payload.get("cols", 120))
                        rows = int(payload.get("rows", 30))
                        client.api.exec_resize(exec_id, height=rows, width=cols)

            finally:
                stop_event.set()
                try:
                    raw_socket.close()
                except Exception:
                    pass
                try:
                    ws.close()
                except Exception:
                    pass

        except PermissionError as exc:
            _ws_error(ws, str(exc))
        except ValueError as exc:
            _ws_error(ws, str(exc))
        except Exception as exc:
            _ws_error(ws, f"Unable to open shell: {exc}")
