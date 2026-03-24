# LTI-Shell Latest Updates

Date: March 24, 2026

## Summary

This update includes a working sandbox MVP plus lifecycle hardening:

1. Moodle launch
2. Create attempt
3. Start isolated Docker container
4. Open browser terminal (xterm.js over WebSocket)
5. Reset/terminate attempt
6. Auto-expire inactive attempts
7. Write audit logs for key events

## Backend Changes

### Attempt lifecycle model

- Added `Attempt` model in `backend/models/attempt.py`
- Core fields:
  - `attempt_id`
  - `user_sub`
  - `resource_link_id`
  - `container_id`
  - `status`
  - `created_at`
  - `last_activity_at`
  - `expires_at`

Inactivity behavior:

- Default expiration is now **15 minutes of inactivity**
- Timeout is refreshed on attempt interactions and terminal activity
- Configurable via `LTI_SHELL_ATTEMPT_INACTIVITY_MINUTES`

### Database startup

- App startup initializes DB tables via `init_db()`
- SQLAlchemy + SQLite local development flow confirmed
- SQLite path is anchored to `backend/lti_shell.db` for consistency

### Docker lifecycle service

Implemented in `backend/services/docker_service.py`:

- `create_attempt_container()`
- `reset_attempt_container(container_id)`
- `terminate_attempt_container(container_id)`
- `get_container_status(container_id)`

Security/runtime controls:

- `network_disabled=True`
- Non-root user (`65534:65534` by default)
- Drop all capabilities (`cap_drop=["ALL"]`)
- `no-new-privileges:true`
- CPU and memory limits
- PID limit
- Read-only filesystem + tmpfs mounts
- Auto-remove containers after stop

### Auto-expiration cleanup worker

Implemented in `backend/services/attempt_cleanup_service.py`:

- Background worker scans for expired active attempts
- Terminates expired containers
- Marks attempts as `expired`
- Cleanup interval is configurable via `LTI_SHELL_CLEANUP_INTERVAL_SECONDS` (default `30`)

### Attempt API routes

Implemented in `backend/routes/assignments.py`:

- `POST /api/attempts`
- `POST /api/attempts/<attempt_id>/reset`
- `POST /api/attempts/<attempt_id>/terminate`
- `GET /api/attempts/<attempt_id>`

Route behavior includes:

- Session auth validation (`session["user"]`)
- Access control by `user.sub` and `resource_link_id`
- DB persistence for attempt/container state
- Activity touch updates (`last_activity_at`, `expires_at`)

### Terminal WebSocket route

Implemented in `backend/routes/terminal.py`:

- `GET /ws/terminal?attempt_id=<attempt_id>`

Behavior:

- Verifies user access to attempt
- Attaches to container shell (`/bin/bash`) via Docker exec
- Streams terminal output to browser
- Accepts keyboard input and terminal resize events
- Touches attempt activity while terminal is in use

### Audit logging

Implemented:

- `AuditLog` model in `backend/models/audit_log.py`
- `log_event()` helper in `backend/services/audit_service.py`
- Event writes for:
  - LTI launch validation
  - Attempt created/reset/terminated
  - Attempt lifecycle failures
  - Auto-expiration events

### App wiring

Updated `backend/app.py` to:

- Register assignments API blueprint
- Initialize `flask-sock` (`Sock(app)`)
- Register terminal socket route (`register_terminal_socket(sock)`)
- Start attempt cleanup worker on app startup (with debug reloader guard)

### Dependencies

`backend/requirements.txt` includes:

- `SQLAlchemy==2.0.38`
- `docker==7.1.0`
- `flask-sock==0.7.0`

## Frontend Changes

### Assignment workspace

Updated `frontend/pages/assignment-view.html`:

- Attempt controls:
  - Start Attempt
  - Reset Attempt
  - Terminate Attempt
  - Refresh Status
- Attempt status table
- Embedded xterm.js terminal panel

### Client API helpers

Updated `frontend/js/api.js`:

- `createAttempt()`
- `resetAttempt(attemptId)`
- `terminateAttempt(attemptId)`
- `getAttempt(attemptId)`

### Terminal controller

Updated `frontend/js/terminal.js`:

- Opens/closes terminal WebSocket
- Sends keyboard input and resize messages
- Renders backend terminal output
- Reconnects based on attempt state
- Sends best-effort terminate request on page exit (`beforeunload`/`pagehide`)

## Verification Checklist

1. Launch tool from Moodle.
2. Open Assignment View.
3. Click Start Attempt.
4. Confirm attempt and container status are shown.
5. Run commands in terminal (for example: `pwd`, `ls`).
6. Click Reset Attempt and verify container replacement.
7. Click Terminate Attempt and verify status is `terminated`.
8. Leave Assignment page and verify attempt is terminated on exit.
9. Leave attempt idle for >15 minutes and verify status becomes `expired`.
10. Confirm events are written to `audit_logs` table.

## Known Next Steps

- Instructor assignment configuration UI
- Automated grading feature integration
- LMS AGS grade passback
- Submission history + instructor review flow
