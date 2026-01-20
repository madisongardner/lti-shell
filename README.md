# LTI-Shell

An LTI 1.3–compliant web application that provides a secure, containerized Bash sandbox with automated grading for LMS-integrated assignments.

## Project Overview
LTI-Shell is a senior capstone project for **CS 496: Senior Project and Professional Practice**. The system integrates with a Learning Management System (LMS) using the LTI 1.3 standard to launch a disposable Linux environment where students can complete Bash-based programming assignments. Submissions are automatically graded using instructor-defined test scripts, and grades are returned directly to the LMS.

The project emphasizes professional software engineering practices including secure authentication, container isolation, automated testing, documentation, and iterative development.

## Key Features
- LTI 1.3–compliant authentication and launch
- LMS integration using Moodle (open-source LMS)
- Disposable, containerized Bash sandbox per student attempt
- Browser-based command execution interface
- Automated grading using Bash test scripts
- Grade passback to LMS gradebook
- Secure sandboxing with resource limits

## Technology Stack
- **Backend:** (to be finalized by team, e.g., FastAPI / Node.js / ASP.NET Core)
- **Frontend:** Web-based UI for command execution and feedback
- **LMS:** Moodle (development and testing)
- **Sandboxing:** Docker containers
- **Database:** SQLite (local development), PostgreSQL (deployment)
- **Authentication:** LTI 1.3 (OIDC + OAuth 2.0)

## Repository Structure (Planned)
/app # Web application (LTI tool provider)
/sandbox # Docker sandbox images and runner logic
/tests # Assignment test script templates
/docs # SRS, design docs, diagrams
/scripts # Utility and deployment scripts


## Development Status
This project is under active development as part of the Spring 2026 semester. Features will be implemented incrementally according to a defined sprint plan.

## Usage Notes
- This repository is intended for academic use.
- AI tools may only be used in accordance with course policy.
- All contributors must adhere to the project scope and design document.

## Team
- Senior Capstone Team, Western Kentucky University

## License
This project is developed for educational purposes. Licensing details will be finalized prior to deployment.

