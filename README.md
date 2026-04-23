# LTI-Shell

An LTI 1.3–compliant web application that provides a secure, containerized Bash sandbox with automated grading for LMS-integrated assignments.

## Project Overview
LTI-Shell is a senior capstone project for **CS 496: Senior Project and Professional Practice**. The system integrates with a Learning Management System (LMS) using the LTI 1.3 standard to launch a disposable Linux environment where students can complete Bash-based programming assignments. Submissions are automatically graded using instructor-defined test scripts, and grades are returned directly to the LMS.

The project emphasizes professional software engineering practices including secure authentication, container isolation, automated testing, documentation, and iterative development.

## Key Features
- LTI 1.3–compliant authentication and launch
- LMS integration using Moodle (open-source LMS)
- Role-based views (teacher dashboard / student dashboard)
- Disposable, containerized Bash sandbox per student attempt
- Browser-based command execution interface
- Automated grading using Bash test scripts
- Grade passback to LMS gradebook
- Starter files automatically copied into `/workspace` on attempt create/reset
- Secure sandboxing with resource limits

## Technology Stack
- **Backend:** Python / Flask
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **LMS:** Moodle (development and testing via Docker)
- **LTI Library:** PyLTI1p3
- **Sandboxing:** Docker containers
- **Database:** SQLite (local development), PostgreSQL (deployment)
- **Authentication:** LTI 1.3 (OIDC + OAuth 2.0)

## Repository Structure

```
lti-shell/
├── backend/
│   ├── app.py                  # Flask application entry point
│   ├── config.py               # Flask configuration (sessions, cache, LTI paths)
│   ├── extensions.py           # Flask extension instances (Cache, Session)
│   ├── requirements.txt        # Python dependencies
│   ├── configs/
│   │   ├── lti.json            # LTI platform configuration (Moodle connection)
│   │   ├── private.key         # RSA private key (generated locally, not committed)
│   │   └── public.key          # RSA public key (generated locally, not committed)
│   ├── routes/
│   │   ├── lti.py              # LTI endpoints (login, launch, JWKS)
│   │   ├── assignments.py      # Assignment CRUD (planned)
│   │   ├── terminal.py         # Terminal execution (planned)
│   │   └── docker_manager.py   # Docker management (planned)
│   ├── services/
│   │   ├── lti_service.py      # LTI role parsing and user data extraction
│   │   ├── grading_service.py  # Grading logic (planned)
│   │   └── docker_service.py   # Container management (planned)
│   └── models/                 # Database models (planned)
├── frontend/
│   ├── index.html              # Landing page
│   ├── css/styles.css          # Shared styles
│   ├── js/
│   │   ├── api.js              # API fetch utilities
│   │   └── app.js              # Dashboard rendering logic
│   └── pages/
│       ├── student-dashboard.html
│       └── teacher-dashboard.html
├── database/
│   └── schema.sql              # Database schema (planned)
├── docker/
│   └── docker-compose.yml      # Moodle + MariaDB development environment
└── README.md
```

## Prerequisites

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/)
- **OpenSSL** — included with Git Bash on Windows, or install via your package manager

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd lti-shell
```

### 2. Generate RSA Keys

The LTI 1.3 protocol requires an RSA key pair for JWT signing. Generate them in the `backend/configs/` directory:

```bash
mkdir -p backend/configs
openssl genrsa -out backend/configs/private.key 2048
openssl rsa -in backend/configs/private.key -pubout -out backend/configs/public.key
```

These keys are specific to your machine and should **not** be committed to git.

### 3. Set Up the Python Virtual Environment

```bash
python -m venv venv
```

Activate it:

- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **Windows (Git Bash):** `source venv/Scripts/activate`
- **macOS / Linux:** `source venv/bin/activate`

Install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

### 4. Start the Moodle Development Environment

```bash
cd docker
docker compose up -d
```

Moodle will be available at **http://localhost** once it finishes starting (this can take a few minutes on the first run).

- **Admin login:** `admin` / `Admin123!`

### 5. Build the Sandbox Image (vi + common CLI tools)

Build the attempt sandbox image once from the repository root:

```bash
docker build -t lti-shell-sandbox:latest -f docker/sandbox/Dockerfile .
```

This image includes `vim-tiny` (`vi`), `nano`, `less`, `tree`, `jq`, `zip`, `unzip`, and other common Linux utilities.

### 6. Start the Flask Server

From the `backend/` directory (with venv activated):

```bash
cd backend
python app.py
```

The server starts at **http://localhost:5000**. Verify it works:
- http://localhost:5000 — should show the landing page
- http://localhost:5000/lti/jwks — should return JSON with your RSA public key

### 7. Register the LTI Tool in Moodle

1. Log into Moodle as admin
2. Go to **Site administration** > **Plugins** > **Activity modules** > **External tool** > **Manage tools**
3. Click **"configure a tool manually"**
4. Fill in:
   - **Tool name:** `LTI-Shell`
   - **Tool URL:** `http://localhost:5000/lti/launch`
   - **LTI version:** `LTI 1.3`
   - **Public key type:** `Keyset URL`
   - **Public keyset:** `http://host.docker.internal:5000/lti/jwks`
   - **Initiate login URL:** `http://localhost:5000/lti/login`
   - **Redirection URI(s):** `http://localhost:5000/lti/launch`
   - **Default launch container:** `New window`
5. Click **Save changes**

> **Note:** The Public keyset URL uses `host.docker.internal` instead of `localhost` because Moodle runs inside a Docker container and needs to reach the Flask server on your host machine.

### 8. Update LTI Configuration

After saving the tool in Moodle:

1. Find `LTI-Shell` in the tool list and click the **gear icon** to view configuration details
2. Copy the **Client ID** and **Deployment ID**
3. Open `backend/configs/lti.json` and replace the placeholder values:

```json
{
    "http://localhost": [
        {
            "default": true,
            "client_id": "YOUR_CLIENT_ID_HERE",
            "deployment_ids": ["YOUR_DEPLOYMENT_ID_HERE"],
            ...
        }
    ]
}
```

### 9. Test the LTI Launch

1. In Moodle, go to any course (or create one)
2. Turn editing on
3. **Add an activity or resource** > **External tool**
4. Name it (e.g., "Shell Assignment 1"), select `LTI-Shell` as the preconfigured tool
5. Save and click the activity link
6. You should land on either the **Teacher Dashboard** or **Student Dashboard** with your user info displayed

## LTI 1.3 Flow

When a user clicks an LTI activity in Moodle, the following happens:

1. **OIDC Login Initiation** — Moodle sends the user to `/lti/login` with identity hints
2. **Authorization Redirect** — Flask redirects the browser back to Moodle's auth endpoint
3. **JWT Launch** — Moodle validates the request and POSTs a signed JWT to `/lti/launch`
4. **Validation & Session** — Flask validates the JWT, extracts user info and roles, stores them in the session
5. **Dashboard Redirect** — The user is redirected to the teacher or student dashboard based on their LTI role

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
