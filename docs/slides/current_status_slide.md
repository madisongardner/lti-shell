# Slide: LTI-Shell Progress (March 26, 2026)

## What’s Working End-to-End
- LTI 1.3 launch from Moodle into role-based dashboard (teacher/student).
- Student attempt lifecycle: create, terminal session, reset, terminate, auto-expire.
- Secure per-attempt Docker sandbox with resource limits and no network.
- Starter files auto-copied into `/workspace` on attempt create/reset.
- Submission flow runs instructor `run_tests.sh` inside container and captures stdout/stderr.
- Score parsing from `SCORE=<value>` with timeout/fail handling.
- Grade passback to LMS via AGS with retry handling.

## Runtime/Terminal Improvements Completed
- Sandbox image now includes `vi` and common Linux tools.
- Shell startup defaults and history persistence configured.
- Fixed writable workspace permissions for student user.
- Fixed test staging bug (`/tmp/lti_tests`) during grading.

## Current Risks / Gaps
- Grading is integration-tested via live submit flow; no unit/integration test suite yet.
- README architecture notes are partially behind current implementation.

## Next 2 Priorities
1. Add automated tests for grading and attempt lifecycle paths.
2. Add instructor-facing submission/feedback review workflow.
