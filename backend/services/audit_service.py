"""Audit logging helpers."""

import json

from database import SessionLocal
from models.audit_log import AuditLog


def log_event(event_type, actor_sub="", resource_link_id="", details=None):
    """Persist an audit event. Failures are swallowed to avoid breaking primary flows."""
    db = SessionLocal()
    try:
        entry = AuditLog(
            event_type=event_type,
            actor_sub=actor_sub or "",
            resource_link_id=resource_link_id or "",
            details_json=json.dumps(details or {}),
        )
        db.add(entry)
        db.commit()
        return entry.id
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()
