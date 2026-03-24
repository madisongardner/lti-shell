from contextlib import contextmanager

from flask import Blueprint, jsonify, session

from database import SessionLocal
from models.attempt import Attempt
from services.docker_service import (
    create_attempt_container,
    get_container_status,
    reset_attempt_container,
    terminate_attempt_container,
)
from services.attempt_cleanup_service import refresh_attempt_timeout
from services.audit_service import log_event

assignments_bp = Blueprint("assignments", __name__)


@contextmanager
def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_user():
    user = session.get("user")
    if not user:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    if not user.get("sub") or not user.get("resource_link_id"):
        return None, (jsonify({"error": "Missing launch context in session"}), 400)
    return user, None


def _can_access_attempt(user, attempt):
    if user.get("role") == "teacher":
        return attempt.resource_link_id == user.get("resource_link_id")
    return (
        attempt.user_sub == user.get("sub")
        and attempt.resource_link_id == user.get("resource_link_id")
    )


@assignments_bp.route("/attempts", methods=["POST"])
def create_attempt():
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = Attempt(
            user_sub=user["sub"],
            resource_link_id=user["resource_link_id"],
            status="created",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        try:
            container = create_attempt_container()
            attempt.container_id = container["container_id"]
            attempt.status = container.get("docker_status", "running")
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
            log_event(
                "attempt.created",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={
                    "attempt_id": attempt.attempt_id,
                    "container_id": attempt.container_id,
                    "status": attempt.status,
                },
            )
        except Exception as exc:
            attempt.status = "failed"
            db.commit()
            log_event(
                "attempt.create_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to create attempt container: {exc}"}), 500

        return (
            jsonify(
                {
                    "attempt_id": attempt.attempt_id,
                    "status": attempt.status,
                    "container_id": attempt.container_id,
                    "created_at": attempt.created_at.isoformat(),
                    "last_activity_at": attempt.last_activity_at.isoformat(),
                    "expires_at": attempt.expires_at.isoformat(),
                }
            ),
            201,
        )


@assignments_bp.route("/attempts/<attempt_id>/reset", methods=["POST"])
def reset_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            container = reset_attempt_container(attempt.container_id)
            attempt.container_id = container["container_id"]
            attempt.status = container.get("docker_status", "running")
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
            log_event(
                "attempt.reset",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={
                    "attempt_id": attempt.attempt_id,
                    "container_id": attempt.container_id,
                    "status": attempt.status,
                },
            )
        except Exception as exc:
            log_event(
                "attempt.reset_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to reset attempt: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_id": attempt.container_id,
                "last_activity_at": attempt.last_activity_at.isoformat(),
                "expires_at": attempt.expires_at.isoformat(),
            }
        )


@assignments_bp.route("/attempts/<attempt_id>/terminate", methods=["POST"])
def terminate_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            stopped = terminate_attempt_container(attempt.container_id)
            attempt.status = "terminated"
            attempt.container_id = None
            db.commit()
            log_event(
                "attempt.terminated",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "container_stopped": stopped},
            )
        except Exception as exc:
            log_event(
                "attempt.terminate_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to terminate attempt: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_stopped": stopped,
            }
        )


@assignments_bp.route("/attempts/<attempt_id>", methods=["GET"])
def get_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            runtime_status = get_container_status(attempt.container_id)
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
        except Exception as exc:
            return jsonify({"error": f"Failed to get attempt status: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_id": attempt.container_id,
                "docker_status": runtime_status.get("docker_status"),
                "created_at": attempt.created_at.isoformat(),
                "last_activity_at": attempt.last_activity_at.isoformat(),
                "expires_at": attempt.expires_at.isoformat(),
            }
        )
