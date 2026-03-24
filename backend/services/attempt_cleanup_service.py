"""Background cleanup for expired attempts."""

import logging
import os
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import SessionLocal
from models.attempt import Attempt
from services.audit_service import log_event
from services.docker_service import terminate_attempt_container

DEFAULT_CLEANUP_INTERVAL_SECONDS = int(os.getenv('LTI_SHELL_CLEANUP_INTERVAL_SECONDS', '30'))
ATTEMPT_INACTIVITY_MINUTES = int(os.getenv('LTI_SHELL_ATTEMPT_INACTIVITY_MINUTES', '15'))
ACTIVE_ATTEMPT_STATUSES = ('created', 'running')

logger = logging.getLogger(__name__)


def _inactivity_window():
    return timedelta(minutes=ATTEMPT_INACTIVITY_MINUTES)


def refresh_attempt_timeout(attempt, now=None):
    """Refresh inactivity timeout fields on an attempt instance."""
    current_time = now or datetime.now(timezone.utc)
    attempt.last_activity_at = current_time
    attempt.expires_at = current_time + _inactivity_window()


def touch_attempt_activity(attempt_id, now=None):
    """Refresh timeout for one active attempt by id."""
    current_time = now or datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return False
        if attempt.status not in ACTIVE_ATTEMPT_STATUSES:
            return False

        refresh_attempt_timeout(attempt, current_time)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def expire_stale_attempts(now=None):
    """Mark expired attempts and terminate any still-running containers."""
    current_time = now or datetime.now(timezone.utc)
    expired_count = 0

    db = SessionLocal()
    try:
        stmt = (
            select(Attempt)
            .where(Attempt.expires_at <= current_time)
            .where(Attempt.status.in_(ACTIVE_ATTEMPT_STATUSES))
        )
        attempts = db.execute(stmt).scalars().all()

        for attempt in attempts:
            try:
                terminate_attempt_container(attempt.container_id)
            except Exception:
                logger.exception('Failed to terminate expired attempt container: %s', attempt.attempt_id)

            attempt.status = 'expired'
            attempt.container_id = None
            log_event(
                'attempt.expired',
                actor_sub=attempt.user_sub,
                resource_link_id=attempt.resource_link_id,
                details={'attempt_id': attempt.attempt_id},
            )
            expired_count += 1

        if expired_count:
            db.commit()

        return expired_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _cleanup_loop(stop_event, interval_seconds):
    while not stop_event.is_set():
        try:
            expired_count = expire_stale_attempts()
            if expired_count:
                logger.info('Expired attempts cleaned: %s', expired_count)
        except Exception:
            logger.exception('Attempt expiration cleanup failed')

        stop_event.wait(interval_seconds)


def start_attempt_cleanup_worker(interval_seconds=None):
    """Start daemon thread that periodically expires stale attempts."""
    interval = interval_seconds or DEFAULT_CLEANUP_INTERVAL_SECONDS
    stop_event = threading.Event()
    worker = threading.Thread(
        target=_cleanup_loop,
        args=(stop_event, interval),
        daemon=True,
        name='attempt-cleanup-worker',
    )
    worker.start()
    return stop_event, worker
