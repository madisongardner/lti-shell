\documentclass[12pt, letterpaper]{article}

\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{float}

% Code listing style
\definecolor{codebg}{gray}{0.95}
\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{codeblue}{rgb}{0.15,0.25,0.55}

\lstdefinestyle{pythonstyle}{
    backgroundcolor=\color{codebg},
    basicstyle=\ttfamily\small,
    breaklines=true,
    captionpos=b,
    commentstyle=\color{codegreen},
    keywordstyle=\color{codeblue}\bfseries,
    stringstyle=\color{red!60!black},
    numberstyle=\tiny\color{codegray},
    numbers=left,
    numbersep=8pt,
    frame=single,
    rulecolor=\color{black!30},
    tabsize=4,
    showstringspaces=false,
    language=Python,
    morekeywords={self, True, False, None, yield, with, as, assert},
}

\lstdefinestyle{bashstyle}{
    backgroundcolor=\color{codebg},
    basicstyle=\ttfamily\small,
    breaklines=true,
    captionpos=b,
    commentstyle=\color{codegreen},
    keywordstyle=\color{codeblue}\bfseries,
    frame=single,
    rulecolor=\color{black!30},
    tabsize=4,
    showstringspaces=false,
    language=bash,
}

\lstset{style=pythonstyle}

% Header/Footer
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{LTI-Shell Test Plan}
\fancyhead[R]{CS 496 Senior Project}
\fancyfoot[C]{\thepage}

\titleformat{\section}{\Large\bfseries}{}{0em}{}[\titlerule]
\titleformat{\subsection}{\large\bfseries}{}{0em}{}

\begin{document}

% ============================================================
% Title Page
% ============================================================
\begin{titlepage}
    \centering
    \vspace*{2cm}
    {\Huge\bfseries LTI-Shell\par}
    \vspace{0.5cm}
    {\LARGE Software Test Plan\par}
    \vspace{2cm}
    {\Large CS 496 - Senior Project\par}
    {\Large Western Kentucky University\par}
    \vspace{1.5cm}
    {\large Isaac Gentry, Madison Gardner, Cing Dim\par}
    \vspace{1cm}
    {\large April 2026\par}
    \vfill
    {\normalsize Version 1.0\par}
\end{titlepage}

\newpage
\tableofcontents
\newpage

% ============================================================
% 1. Introduction
% ============================================================
\section{Introduction}

\subsection{Purpose}
This document defines the test plan for the LTI-Shell project, a web application that provides containerized Bash sandbox environments integrated with Learning Management Systems (LMS) via the LTI 1.3 standard. The plan describes the testing strategy, scope, test cases, and scripts that will be used to verify the correctness, reliability, and security of the system before deployment.

\subsection{Project Overview}
LTI-Shell enables instructors to create Bash-based programming assignments that students complete inside isolated Docker containers accessed through a browser-based terminal. The system supports:

\begin{itemize}
    \item LTI 1.3 authentication with OIDC and OAuth 2.0
    \item Disposable, sandboxed Docker containers per student attempt
    \item Browser-based terminal via xterm.js and WebSocket
    \item Automated grading via instructor-provided test scripts
    \item Grade passback to the LMS via LTI Assignment and Grade Services (AGS)
    \item Role-based access control (teacher and student dashboards)
    \item Audit logging for all significant events
\end{itemize}

\subsection{Scope of Testing}
Testing covers the following system components:

\begin{itemize}
    \item \textbf{Backend services} --- LTI authentication, assignment management, attempt lifecycle, Docker orchestration, grading engine, AGS grade passback, artifact validation, and audit logging.
    \item \textbf{REST API} --- All endpoints under \texttt{/api/} and \texttt{/lti/}, including authentication, authorization, input validation, and error handling.
    \item \textbf{Frontend} --- Student and teacher dashboards, assignment workspace, terminal integration, and API communication layer.
    \item \textbf{Infrastructure} --- Docker sandbox image security, container resource limits, and automatic cleanup.
\end{itemize}

\subsection{References}
\begin{itemize}
    \item IMS Global LTI 1.3 Specification
    \item IMS Global Assignment and Grade Services (AGS) 2.0
    \item Docker Engine API Documentation
    \item Flask Web Framework Documentation
    \item PyLTI1p3 Library Documentation
\end{itemize}

% ============================================================
% 2. Test Strategy
% ============================================================
\section{Test Strategy}

Testing is organized into four levels, each targeting a different scope of the system:

\begin{enumerate}
    \item \textbf{Unit Testing} --- Validates individual functions and methods in isolation using mocks for external dependencies (Docker, database, LTI platform). Automated with \texttt{pytest}.
    \item \textbf{Integration Testing} --- Verifies that components interact correctly: API routes with database models, Docker service with container runtime, and grading service with the sandbox filesystem.
    \item \textbf{System Testing} --- End-to-end validation of complete user workflows from LTI launch through grading and grade passback, exercised against a running instance with Moodle.
    \item \textbf{Acceptance Testing} --- Confirms the system meets functional requirements and is usable by instructors and students in a realistic classroom scenario.
\end{enumerate}

\subsection{Test Environment}

\begin{longtable}{p{3.5cm} p{10cm}}
    \toprule
    \textbf{Component} & \textbf{Details} \\
    \midrule
    Operating System & macOS / Linux \\
    Python & 3.10+ \\
    Database & SQLite (testing), PostgreSQL (staging) \\
    Docker & Docker Engine 24+ with \texttt{lti-shell-sandbox:latest} image \\
    LMS & Moodle 4.x via Docker Compose \\
    Browser & Chrome, Firefox (latest stable) \\
    Test Framework & pytest 8.x with pytest-flask, pytest-mock \\
    \bottomrule
\end{longtable}

\subsection{Entry and Exit Criteria}

\textbf{Entry Criteria:}
\begin{itemize}
    \item All source code is committed and buildable.
    \item Docker sandbox image builds successfully.
    \item Moodle development instance is accessible via Docker Compose.
    \item Test database is initialized with schema migrations applied.
\end{itemize}

\textbf{Exit Criteria:}
\begin{itemize}
    \item All unit tests pass with $\geq$90\% line coverage on backend services.
    \item All integration tests pass against a live database and Docker daemon.
    \item All system test scenarios complete successfully.
    \item All critical and high-severity acceptance criteria are met.
    \item No unresolved critical or high-severity defects remain.
\end{itemize}

% ============================================================
% 3. Unit Testing
% ============================================================
\section{Unit Testing}

Unit tests target individual functions and classes in the backend. External dependencies (Docker daemon, database, LTI platform) are mocked to ensure tests run fast and deterministically.

\subsection{Test Cases}

\subsubsection{Grading Service --- \texttt{grading\_service.py}}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U1 & Score extraction with explicit SCORE & Verify \texttt{\_extract\_score} parses ``SCORE=85'' from stdout and returns 85.0 \\
    U2 & Score extraction with decimal & Verify ``SCORE = 7.5'' is parsed correctly as 7.5 \\
    U3 & Score clamped to max & Verify a SCORE value exceeding \texttt{max\_points} is clamped \\
    U4 & Score defaults on pass & Verify full marks returned when exit code is 0 and no explicit SCORE \\
    U5 & Score defaults on fail & Verify 0.0 returned when exit code is non-zero and no explicit SCORE \\
    U6 & Timeout status detection & Verify exit code 124 maps to ``timeout'' status \\
    U7 & Missing container ID & Verify \texttt{run\_grading\_for\_attempt} raises ValueError for None container \\
    U8 & Missing tests path & Verify ValueError raised when assignment has no \texttt{tests\_extracted\_path} \\
    U9 & Test tar construction & Verify \texttt{\_build\_tests\_tar\_bytes} creates a valid tar with ``lti\_tests/'' prefix \\
    \bottomrule
\end{longtable}

\subsubsection{Docker Service --- \texttt{docker\_service.py}}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U10 & User ID parsing (uid:gid) & Verify \texttt{\_user\_ids("65532:65532")} returns (65532, 65532) \\
    U11 & User ID parsing (uid only) & Verify \texttt{\_user\_ids("1000")} returns (1000, 1000) \\
    U12 & User ID parsing (invalid) & Verify \texttt{\_user\_ids("abc")} returns the default (65532, 65532) \\
    U13 & Container create params & Verify \texttt{create\_attempt\_container} calls Docker with correct security flags \\
    U14 & Terminate missing container & Verify \texttt{terminate\_attempt\_container(None)} returns False \\
    U15 & Terminate not-found container & Verify NotFound exception is handled and returns False \\
    U16 & Workspace tar ownership & Verify \texttt{\_build\_dir\_tar\_bytes} normalizes uid/gid on all entries \\
    U17 & Populate with no starter & Verify \texttt{populate\_workspace\_from\_starter} returns copied=False when path is None \\
    \bottomrule
\end{longtable}

\subsubsection{Assignment Artifact Service --- \texttt{assignment\_artifact\_service.py}}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U18 & Reject non-zip file & Verify ArtifactValidationError raised for a \texttt{.tar.gz} upload \\
    U19 & Reject oversized zip & Verify error raised when zip exceeds \texttt{MAX\_UPLOAD\_BYTES} \\
    U20 & Reject zip with symlinks & Verify symlink entries in the archive trigger validation error \\
    U21 & Reject path traversal & Verify archive entries with ``../'' are rejected \\
    U22 & Reject too many files & Verify archive with $>$500 entries is rejected \\
    U23 & Reject missing run\_tests.sh & Verify tests artifact without \texttt{run\_tests.sh} raises error \\
    U24 & Accept valid tests zip & Verify a well-formed tests zip with \texttt{run\_tests.sh} passes validation \\
    U25 & Slug sanitization & Verify \texttt{\_slug} strips special characters and truncates to 80 chars \\
    \bottomrule
\end{longtable}

\subsubsection{LTI AGS Service --- \texttt{lti\_ags\_service.py}}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U26 & Grade object construction & Verify \texttt{\_build\_grade} sets score, max, user ID, and timestamps \\
    U27 & Retry on transient failure & Verify retry logic attempts up to \texttt{max\_attempts} times \\
    U28 & Success on first try & Verify successful passback returns attempts=1, success=True \\
    U29 & All retries exhausted & Verify failure after max attempts returns success=False with error \\
    U30 & Missing launch\_id & Verify ValueError raised when launch\_id is empty \\
    \bottomrule
\end{longtable}

\subsubsection{Attempt Cleanup Service}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U31 & Timeout refresh & Verify \texttt{refresh\_attempt\_timeout} updates \texttt{expires\_at} correctly \\
    U32 & Expire stale attempts & Verify cleanup marks expired attempts and terminates containers \\
    U33 & Skip already terminated & Verify cleanup does not process already terminated attempts \\
    \bottomrule
\end{longtable}

\subsubsection{Route Authorization Helpers}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    U34 & Unauthenticated user & Verify \texttt{\_require\_user} returns 401 when session is empty \\
    U35 & Missing launch context & Verify 400 returned when session lacks \texttt{resource\_link\_id} \\
    U36 & Student cannot access teacher & Verify \texttt{\_require\_teacher} returns 403 for student role \\
    U37 & Cross-resource access denied & Verify \texttt{\_can\_access\_attempt} returns False for mismatched resource \\
    U38 & Assignment payload validation & Verify \texttt{\_validate\_assignment\_payload} rejects empty title \\
    U39 & Due date parsing & Verify ISO 8601 strings with and without timezone are parsed correctly \\
    U40 & Max points coercion & Verify negative and zero values raise ValueError \\
    \bottomrule
\end{longtable}

\subsection{Unit Test Scripts}

All unit tests are implemented as \texttt{pytest} test files using \texttt{unittest.mock} for dependency isolation. A shared \texttt{conftest.py} configures the Python path so that backend module imports resolve correctly. The test scripts are organized as follows:

\begin{longtable}{p{6.5cm} p{4cm} p{3cm}}
    \toprule
    \textbf{Test File} & \textbf{Module Under Test} & \textbf{Test Cases} \\
    \midrule
    \texttt{tests/unit/test\_grading\_service.py} & \texttt{grading\_service.py} & U1--U9 \\
    \texttt{tests/unit/test\_docker\_service.py} & \texttt{docker\_service.py} & U10--U17 \\
    \texttt{tests/unit/test\_artifact\_service.py} & \texttt{assignment\_artifact\_service.py} & U18--U25 \\
    \texttt{tests/unit/test\_route\_helpers.py} & \texttt{routes/assignments.py} & U34--U40 \\
    \bottomrule
\end{longtable}

Tests can be executed from the project root with:

\begin{lstlisting}[style=bashstyle]
python -m pytest tests/unit/ -v
\end{lstlisting}

\noindent The full source code for each test script is provided in Appendix~\ref{appendix:scripts}.

% ============================================================
% 4. Integration Testing
% ============================================================
\section{Integration Testing}

Integration tests verify that system components work together correctly. Unlike unit tests, these tests interact with real infrastructure: a live SQLite database, the Docker daemon, and the Flask application context.

\subsection{Test Cases}

\subsubsection{API + Database Integration}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    I1 & Create assignment via API & POST to \texttt{/api/assignments} with valid payload creates a database record and returns 201 with correct fields \\
    I2 & Duplicate assignment rejected & POST to the same course and resource\_link\_id returns 409 Conflict \\
    I3 & Update assignment via PATCH & PATCH to \texttt{/api/assignments/<id>} modifies title and persists the change in the database \\
    I4 & List assignments filtered by course & GET \texttt{/api/assignments} returns only assignments for the authenticated user's course \\
    I5 & Upload starter ZIP & POST multipart upload to \texttt{/api/assignments/<id>/starter-upload} stores the file and updates assignment record \\
    I6 & Upload tests ZIP with validation & POST tests ZIP triggers validation; \texttt{has\_required\_test\_runner} flag is set correctly \\
    I7 & Assignment configuration check & After uploading both artifacts and setting all fields, \texttt{is\_configured} becomes True \\
    \bottomrule
\end{longtable}

\subsubsection{Attempt Lifecycle + Docker Integration}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    I8 & Create attempt spawns container & POST \texttt{/api/attempts} creates an Attempt record and a running Docker container \\
    I9 & Attempt reset replaces container & POST \texttt{/api/attempts/<id>/reset} terminates old container and creates a new one with a different ID \\
    I10 & Attempt termination cleans up & POST \texttt{/api/attempts/<id>/terminate} stops the container, sets status to ``terminated'' \\
    I11 & Starter files copied to workspace & After attempt creation, starter files are present in the container's \texttt{/workspace} directory \\
    I12 & Expired attempts auto-cleaned & After inactivity timeout, the cleanup worker marks the attempt expired and stops its container \\
    \bottomrule
\end{longtable}

\subsubsection{Grading + Submission Integration}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    I13 & Submit triggers grading & POST \texttt{/api/attempts/<id>/submit} runs \texttt{run\_tests.sh} inside the container and records the score \\
    I14 & Grading output captured & Submission record contains stdout and stderr from the test execution \\
    I15 & Score persisted correctly & The parsed SCORE value is stored on the Submission and matches expected output \\
    I16 & Container terminated after submit & After submission completes, the attempt's container is stopped and attempt status is ``submitted'' \\
    I17 & Submission list for attempt & GET \texttt{/api/attempts/<id>/submissions} returns all submissions ordered by creation date \\
    \bottomrule
\end{longtable}

\subsubsection{Audit Logging Integration}

\begin{longtable}{p{0.5cm} p{4.5cm} p{8.5cm}}
    \toprule
    \textbf{ID} & \textbf{Test Case} & \textbf{Description} \\
    \midrule
    I18 & Assignment creation logged & Creating an assignment produces an ``assignment.created'' audit log entry \\
    I19 & Attempt lifecycle logged & Creating, resetting, and terminating attempts each produce corresponding audit entries \\
    I20 & Grading events logged & Submission grading produces ``grading.started'' and ``grading.completed'' entries \\
    \bottomrule
\end{longtable}

% ============================================================
% 5. System Testing
% ============================================================
\section{System Testing}

System tests validate complete end-to-end workflows against a fully running LTI-Shell instance connected to a Moodle LMS. These tests are executed manually or with browser automation tools against the Docker Compose development environment.

\subsection{Test Scenarios}

\subsubsection{S1: LTI Launch and Authentication}

\begin{enumerate}
    \item Navigate to the LTI activity link in Moodle as a student.
    \item Verify the OIDC login redirect occurs (browser redirects to Moodle, then back).
    \item Verify the student dashboard loads with the correct user name and role.
    \item Verify the session contains the expected LTI claims (sub, course\_id, resource\_link\_id).
    \item Repeat the launch as a teacher and verify the teacher dashboard loads instead.
\end{enumerate}

\textbf{Expected Result:} Both student and teacher roles land on their respective dashboards with correct identity information extracted from LTI claims.

\subsubsection{S2: Teacher Assignment Configuration}

\begin{enumerate}
    \item Launch as a teacher into the teacher dashboard.
    \item Create a new assignment with title, instructions, due date, and max points.
    \item Upload a valid starter ZIP file.
    \item Upload a valid tests ZIP file containing \texttt{run\_tests.sh}.
    \item Verify the assignment status shows ``Configured'' with all validation checks passing.
    \item Update the assignment title and verify the change persists.
\end{enumerate}

\textbf{Expected Result:} Assignment is fully configured and visible to students launched into the same activity.

\subsubsection{S3: Student Attempt and Terminal Interaction}

\begin{enumerate}
    \item Launch as a student into a configured assignment.
    \item Click ``Start Attempt'' and verify a terminal appears in the browser.
    \item Type shell commands (\texttt{ls}, \texttt{pwd}, \texttt{cat}) and verify output renders correctly.
    \item Verify starter files are present in \texttt{/workspace}.
    \item Verify the container has no network access (\texttt{ping} fails).
    \item Verify resource limits are enforced (memory, CPU, PID count).
\end{enumerate}

\textbf{Expected Result:} Student has a functional, isolated Bash shell with starter files pre-populated and security restrictions enforced.

\subsubsection{S4: Submission and Automated Grading}

\begin{enumerate}
    \item With an active attempt, modify files in \texttt{/workspace} to produce a passing solution.
    \item Click ``Submit for Grading.''
    \item Verify the grading executes and a score is displayed.
    \item Verify stdout/stderr feedback is shown to the student.
    \item Verify the attempt status changes to ``submitted'' and the terminal disconnects.
    \item Verify the container is terminated after submission.
\end{enumerate}

\textbf{Expected Result:} Grading produces a correct score, feedback is visible, and the container is cleaned up.

\subsubsection{S5: LTI AGS Grade Passback}

\begin{enumerate}
    \item Complete a graded submission (scenario S4).
    \item Navigate to the Moodle gradebook for the course.
    \item Verify the student's grade appears with the correct score and max points.
    \item Verify the submission record shows \texttt{passback\_status = "succeeded"}.
\end{enumerate}

\textbf{Expected Result:} The grade appears in Moodle's gradebook matching the score from the grading output.

\subsubsection{S6: Attempt Expiration and Cleanup}

\begin{enumerate}
    \item Start an attempt but do not interact with it for 15+ minutes.
    \item Verify the attempt status transitions to ``expired.''
    \item Verify the Docker container is stopped and removed.
    \item Verify an audit log entry is created for the expiration event.
\end{enumerate}

\textbf{Expected Result:} Inactive attempts are automatically expired and their resources reclaimed.

\subsubsection{S7: Error Recovery}

\begin{enumerate}
    \item Submit an attempt where the test script exits with a non-zero code.
    \item Verify the submission status is ``failed'' with score 0.
    \item Submit an attempt where the test script exceeds the grading timeout.
    \item Verify the submission status is ``timeout.''
    \item Attempt to create an attempt when Docker is unavailable.
    \item Verify a clear error message is returned and the attempt is marked ``failed.''
\end{enumerate}

\textbf{Expected Result:} All error conditions are handled gracefully with appropriate status codes and user-facing messages.

% ============================================================
% 6. Acceptance Testing
% ============================================================
\section{Acceptance Testing}

Acceptance tests confirm that the system meets the functional requirements from the perspective of end users (instructors and students). These tests are performed by stakeholders or representative users against a staging environment.

\subsection{Acceptance Criteria}

\begin{longtable}{p{0.5cm} p{4cm} p{4cm} p{5cm}}
    \toprule
    \textbf{ID} & \textbf{Criterion} & \textbf{Verification Method} & \textbf{Pass Condition} \\
    \midrule
    A1 & LTI 1.3 launch from Moodle & Launch activity from Moodle & User arrives at correct dashboard without manual login \\
    A2 & Role-based dashboard routing & Launch as student and teacher & Each role sees only their designated dashboard \\
    A3 & Assignment creation & Teacher creates assignment & Assignment appears in the system with all fields saved \\
    A4 & Artifact upload and validation & Upload starter and tests ZIPs & ZIPs are validated, extracted, and assignment becomes configured \\
    A5 & Sandbox isolation & Student interacts with terminal & No network access; resource limits enforced; non-root user \\
    A6 & Terminal responsiveness & Type commands in terminal & Commands execute and output displays within 1 second \\
    A7 & Automated grading accuracy & Submit known-correct solution & Score matches expected full marks \\
    A8 & Automated grading for failures & Submit known-incorrect solution & Score is 0 or partial with appropriate feedback \\
    A9 & Grade passback to Moodle & Complete a graded submission & Grade appears in Moodle gradebook \\
    A10 & Attempt reset & Reset an active attempt & New container with fresh starter files; old container removed \\
    A11 & Attempt expiration & Leave attempt idle & Attempt expires after configured timeout \\
    A12 & Multiple submissions & Submit, reset, submit again & Both submissions are recorded with independent scores \\
    A13 & Concurrent students & Multiple students launch simultaneously & Each student gets an independent container and session \\
    A14 & Audit trail completeness & Review audit logs after workflow & All key events are logged with correct actor and details \\
    A15 & Error messaging & Trigger various error conditions & User-facing error messages are clear and actionable \\
    \bottomrule
\end{longtable}

\subsection{Acceptance Test Procedures}

\subsubsection{A1--A2: Authentication and Routing}

\begin{enumerate}
    \item Log into Moodle as an enrolled student.
    \item Navigate to the course and click the LTI-Shell activity.
    \item Verify the student dashboard loads showing the student's name.
    \item Log out and log into Moodle as the course instructor.
    \item Click the same LTI-Shell activity.
    \item Verify the teacher dashboard loads with assignment management controls.
\end{enumerate}

\subsubsection{A3--A4: Assignment Setup}

\begin{enumerate}
    \item As a teacher, click ``Create Assignment.''
    \item Fill in title: ``Bash Basics,'' instructions, due date, and 100 max points.
    \item Upload \texttt{starter.zip} containing a template \texttt{solution.sh} file.
    \item Upload \texttt{tests.zip} containing \texttt{run\_tests.sh} and test data.
    \item Verify the assignment status indicator shows ``Configured'' (green).
    \item Verify all configuration reasons are cleared.
\end{enumerate}

\subsubsection{A5--A6: Sandbox Verification}

\begin{enumerate}
    \item As a student, start an attempt on the configured assignment.
    \item In the terminal, run \texttt{whoami} and verify the user is non-root.
    \item Run \texttt{ping 8.8.8.8} and verify it fails (network disabled).
    \item Run \texttt{ls /workspace} and verify starter files are present.
    \item Run a simple command and verify output appears within 1 second.
    \item Attempt to write outside \texttt{/workspace} and \texttt{/tmp} and verify it fails.
\end{enumerate}

\subsubsection{A7--A9: Grading and Grade Passback}

\begin{enumerate}
    \item Complete the assignment by writing a correct \texttt{solution.sh}.
    \item Click ``Submit for Grading.''
    \item Verify the score displayed is 100/100.
    \item Verify test output feedback is shown.
    \item Navigate to Moodle gradebook and verify the grade of 100 appears.
    \item Reset the attempt, submit an intentionally wrong solution.
    \item Verify the score is less than 100 with failure feedback.
\end{enumerate}

\subsubsection{A10--A12: Attempt Lifecycle}

\begin{enumerate}
    \item Start an attempt and note the container ID from the attempt status.
    \item Click ``Reset Attempt'' and verify a new container ID is assigned.
    \item Verify starter files are re-populated in the new container.
    \item Submit a solution, then start a new attempt.
    \item Verify both submissions appear in the submission history.
\end{enumerate}

\subsubsection{A13: Concurrency}

\begin{enumerate}
    \item Open two browser sessions logged in as different Moodle students.
    \item Both students launch the same assignment activity simultaneously.
    \item Verify each student receives an independent container and terminal session.
    \item Both students submit and receive independent scores.
\end{enumerate}

\subsubsection{A14--A15: Audit and Error Handling}

\begin{enumerate}
    \item After completing the above scenarios, query the audit log table.
    \item Verify entries exist for: assignment creation, attempt creation/reset/termination, submission, grading, and passback events.
    \item Trigger an error (e.g., upload an invalid ZIP) and verify the error message is descriptive and does not expose internal details.
\end{enumerate}

% ============================================================
% 7. Risk and Mitigation
% ============================================================
\section{Risk and Mitigation}

\begin{longtable}{p{4cm} p{3cm} p{6.5cm}}
    \toprule
    \textbf{Risk} & \textbf{Likelihood} & \textbf{Mitigation} \\
    \midrule
    Docker daemon unavailable during tests & Medium & Integration tests check Docker availability before execution; unit tests mock Docker entirely \\
    Moodle version incompatibility & Low & Pin Moodle Docker image version in \texttt{docker-compose.yml}; test against same version used in production \\
    LTI token expiration during long tests & Medium & System tests use fresh launches; AGS tests mock token refresh \\
    Flaky container startup timing & Medium & Integration tests include retry logic with exponential backoff for container readiness checks \\
    Test pollution between runs & Low & Each integration test uses an isolated database transaction that is rolled back after the test \\
    \bottomrule
\end{longtable}

% ============================================================
% 8. Test Execution Schedule
% ============================================================
\section{Test Execution Schedule}

\begin{longtable}{p{3cm} p{3cm} p{4cm} p{3.5cm}}
    \toprule
    \textbf{Phase} & \textbf{Duration} & \textbf{Activities} & \textbf{Dependencies} \\
    \midrule
    Unit Testing & 1 week & Write and execute all unit tests; achieve coverage targets & Source code complete \\
    Integration Testing & 1 week & API + DB tests, Docker lifecycle tests, grading pipeline tests & Unit tests passing, Docker available \\
    System Testing & 1 week & End-to-end scenarios S1--S7 against Moodle dev environment & Integration tests passing, Moodle configured \\
    Acceptance Testing & 1 week & Stakeholder walkthroughs of criteria A1--A15 & System tests passing \\
    \bottomrule
\end{longtable}

% ============================================================
% 9. Defect Management
% ============================================================
\section{Defect Management}

Defects discovered during testing will be tracked using GitHub Issues on the project repository. Each defect will include:

\begin{itemize}
    \item \textbf{Severity:} Critical, High, Medium, Low
    \item \textbf{Test phase:} Unit, Integration, System, or Acceptance
    \item \textbf{Steps to reproduce:} Minimal sequence to trigger the defect
    \item \textbf{Expected vs. actual behavior}
    \item \textbf{Assignee and resolution status}
\end{itemize}

\textbf{Severity Definitions:}
\begin{itemize}
    \item \textbf{Critical} --- System is unusable; data loss or security vulnerability (e.g., container escape, grade corruption).
    \item \textbf{High} --- Major feature is broken with no workaround (e.g., grading fails, LTI launch fails).
    \item \textbf{Medium} --- Feature is degraded but workaround exists (e.g., cleanup worker stalls, UI rendering issue).
    \item \textbf{Low} --- Minor cosmetic or non-functional issue (e.g., log message typo, UI alignment).
\end{itemize}

% ============================================================
% Appendix: Unit Test Scripts
% ============================================================
\newpage
\appendix
\section{Unit Test Script Source Code}
\label{appendix:scripts}

The following pages contain the complete source code for each unit test file referenced in Section~3.

\subsection{tests/unit/test\_grading\_service.py}

\begin{lstlisting}[style=pythonstyle]
"""Unit tests for grading_service.py."""
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.grading_service import (
    _build_tests_tar_bytes,
    _extract_score,
    run_grading_for_attempt,
)


class TestExtractScore:
    """Tests U1-U5: score extraction logic."""

    def test_explicit_score_from_stdout(self):
        """U1: Parse 'SCORE=85' from stdout."""
        score = _extract_score("SCORE=85", "", 100.0, True)
        assert score == 85.0

    def test_decimal_score(self):
        """U2: Parse 'SCORE = 7.5' correctly."""
        score = _extract_score("SCORE = 7.5", "", 10.0, True)
        assert score == 7.5

    def test_score_clamped_to_max(self):
        """U3: Score exceeding max_points is clamped."""
        score = _extract_score("SCORE=150", "", 100.0, True)
        assert score == 100.0

    def test_score_clamped_to_zero(self):
        """U3b: Negative score is clamped to zero."""
        score = _extract_score("SCORE=-5", "", 100.0, True)
        assert score == 0.0

    def test_default_full_marks_on_pass(self):
        """U4: No SCORE token and passed gives full marks."""
        score = _extract_score("All tests passed", "", 100.0, True)
        assert score == 100.0

    def test_default_zero_on_fail(self):
        """U5: No SCORE token and failed gives zero."""
        score = _extract_score("Tests failed", "", 100.0, False)
        assert score == 0.0


class TestRunGrading:
    """Tests U6-U8: grading execution edge cases."""

    def test_timeout_status(self):
        """U6: Exit code 124 maps to 'timeout' status."""
        mock_assignment = MagicMock()
        mock_assignment.tests_extracted_path = "/fake/tests"
        mock_assignment.max_points = 100.0

        mock_attempt = MagicMock()
        mock_attempt.container_id = "abc123"

        mock_container = MagicMock()
        mock_container.id = "abc123"
        exec_result = MagicMock()
        exec_result.exit_code = 124
        exec_result.output = (b"", b"")
        mock_container.exec_run.return_value = exec_result

        with patch("services.grading_service._docker_client") as mock_dc, \
             patch("services.grading_service._build_tests_tar_bytes") as mock_tar, \
             patch("services.grading_service._stage_tests_in_container"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=True):
            mock_dc.return_value.containers.get.return_value = mock_container
            mock_tar.return_value = b"fake_tar"
            result = run_grading_for_attempt(mock_assignment, mock_attempt)

        assert result["status"] == "timeout"
        assert result["exit_code"] == 124

    def test_missing_container_id(self):
        """U7: Raises ValueError when container_id is None."""
        mock_attempt = MagicMock()
        mock_attempt.container_id = None
        with pytest.raises(ValueError, match="no active container"):
            run_grading_for_attempt(MagicMock(), mock_attempt)

    def test_missing_tests_path(self):
        """U8: Raises ValueError when tests are not configured."""
        mock_attempt = MagicMock()
        mock_attempt.container_id = "abc123"
        mock_assignment = MagicMock()
        mock_assignment.tests_extracted_path = None
        with pytest.raises(ValueError, match="not configured"):
            run_grading_for_attempt(mock_assignment, mock_attempt)


class TestBuildTestsTar:
    """Test U9: tar archive construction."""

    def test_tar_has_lti_tests_prefix(self, tmp_path):
        """U9: Tar entries are prefixed with lti_tests/."""
        test_file = tmp_path / "run_tests.sh"
        test_file.write_text("#!/bin/bash\necho SCORE=100")

        tar_bytes = _build_tests_tar_bytes(tmp_path)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tf:
            names = tf.getnames()
            assert any("lti_tests/run_tests.sh" in n for n in names)
\end{lstlisting}

\subsection{tests/unit/test\_docker\_service.py}

\begin{lstlisting}[style=pythonstyle]
"""Unit tests for docker_service.py."""
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import NotFound

from services.docker_service import (
    _user_ids,
    create_attempt_container,
    terminate_attempt_container,
    populate_workspace_from_starter,
)


class TestUserIds:
    """Tests U10-U12: UID/GID parsing."""

    def test_uid_gid_pair(self):
        """U10: Standard uid:gid string."""
        assert _user_ids("65532:65532") == (65532, 65532)

    def test_uid_only(self):
        """U11: UID only defaults GID to same value."""
        assert _user_ids("1000") == (1000, 1000)

    def test_invalid_returns_default(self):
        """U12: Non-numeric input returns defaults."""
        assert _user_ids("abc") == (65532, 65532)


class TestCreateContainer:
    """Test U13: Container creation parameters."""

    @patch("services.docker_service._client")
    def test_security_flags(self, mock_client_fn):
        """U13: Verify container runs with security hardening."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "test123"
        mock_container.status = "running"
        mock_client.containers.run.return_value = mock_container
        mock_client_fn.return_value = mock_client

        result = create_attempt_container()

        call_kwargs = mock_client.containers.run.call_args[1]
        assert call_kwargs["network_disabled"] is True
        assert call_kwargs["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in call_kwargs["security_opt"]
        assert call_kwargs["pids_limit"] == 128
        assert result["container_id"] == "test123"


class TestTerminateContainer:
    """Tests U14-U15: Container termination."""

    def test_none_container(self):
        """U14: None container_id returns False."""
        assert terminate_attempt_container(None) is False

    @patch("services.docker_service._client")
    def test_not_found_returns_false(self, mock_client_fn):
        """U15: NotFound exception returns False."""
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("gone")
        mock_client_fn.return_value = mock_client
        assert terminate_attempt_container("missing") is False


class TestPopulateWorkspace:
    """Tests U16-U17: Workspace population."""

    def test_no_starter_path(self):
        """U17: Returns copied=False when starter path is None."""
        result = populate_workspace_from_starter("abc123", None)
        assert result["copied"] is False
        assert result["file_count"] == 0
\end{lstlisting}

\subsection{tests/unit/test\_artifact\_service.py}

\begin{lstlisting}[style=pythonstyle]
"""Unit tests for assignment_artifact_service.py."""
import io
import os
import stat
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.assignment_artifact_service import (
    ArtifactValidationError,
    _slug,
    _validate_zip_file,
    save_assignment_archive,
)


class TestSlug:
    """Test U25: Slug sanitization."""

    def test_strips_special_chars(self):
        """U25: Special characters are replaced with underscores."""
        assert _slug("My Course! @#$") == "My_Course"

    def test_truncates_to_80(self):
        """U25b: Long strings are truncated."""
        long_name = "a" * 200
        assert len(_slug(long_name)) == 80


class TestValidateZip:
    """Tests U18-U24: ZIP validation."""

    def _make_zip(self, tmp_path, files):
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        return zip_path

    def test_reject_non_zip(self, tmp_path):
        """U18: Non-zip file raises error."""
        bad_file = tmp_path / "fake.zip"
        bad_file.write_text("not a zip file")
        with pytest.raises(ArtifactValidationError, match="valid ZIP"):
            _validate_zip_file(bad_file)

    def test_reject_path_traversal(self, tmp_path):
        """U21: Entries with ../ are rejected."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "pwned")
        with pytest.raises(ArtifactValidationError, match="unsafe"):
            _validate_zip_file(zip_path)

    def test_reject_too_many_files(self, tmp_path):
        """U22: Archives exceeding file count limit are rejected."""
        zip_path = tmp_path / "big.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(501):
                zf.writestr(f"file_{i}.txt", "x")
        with pytest.raises(ArtifactValidationError, match="too many"):
            _validate_zip_file(zip_path)

    def test_reject_missing_test_runner(self, tmp_path):
        """U23: Tests zip without run_tests.sh raises error."""
        zip_path = self._make_zip(tmp_path, {"helper.sh": "echo hi"})
        with pytest.raises(ArtifactValidationError, match="run_tests.sh"):
            _validate_zip_file(zip_path, required_file="run_tests.sh")

    def test_accept_valid_tests_zip(self, tmp_path):
        """U24: Valid tests zip passes validation."""
        zip_path = self._make_zip(tmp_path, {
            "run_tests.sh": "#!/bin/bash\necho SCORE=100",
            "test_helper.sh": "echo helper",
        })
        result = _validate_zip_file(zip_path, required_file="run_tests.sh")
        assert result["has_required_file"] is True
        assert result["file_count"] == 2


class TestSaveArchive:
    """Tests U18-U19: Upload validation in save flow."""

    def test_reject_non_zip_extension(self, tmp_path):
        """U18: Non-.zip filename is rejected."""
        mock_file = MagicMock()
        mock_file.filename = "archive.tar.gz"
        mock_assignment = MagicMock()
        mock_assignment.course_id = "CS101"
        mock_assignment.assignment_id = "a1"
        with pytest.raises(ArtifactValidationError, match=".zip"):
            save_assignment_archive(mock_file, mock_assignment, "starter")
\end{lstlisting}

\subsection{tests/unit/test\_route\_helpers.py}

\begin{lstlisting}[style=pythonstyle]
"""Unit tests for route authorization helpers."""
from unittest.mock import patch

import pytest
from flask import Flask

from routes.assignments import (
    _can_access_attempt,
    _parse_due_at,
    _coerce_max_points,
    _validate_assignment_payload,
)


class TestCanAccessAttempt:
    """Tests U37: Cross-resource access control."""

    def test_student_same_resource(self):
        """U37a: Student can access own attempt."""
        user = {"sub": "user1", "resource_link_id": "rl1", "role": "student"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl1"})()
        assert _can_access_attempt(user, attempt) is True

    def test_student_wrong_resource(self):
        """U37b: Student cannot access another resource's attempt."""
        user = {"sub": "user1", "resource_link_id": "rl1", "role": "student"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl2"})()
        assert _can_access_attempt(user, attempt) is False

    def test_teacher_same_resource(self):
        """U37c: Teacher can access attempts within their resource."""
        user = {"sub": "teacher1", "resource_link_id": "rl1", "role": "teacher"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl1"})()
        assert _can_access_attempt(user, attempt) is True


class TestParseDueAt:
    """Test U39: Due date parsing."""

    def test_iso_with_timezone(self):
        """U39a: ISO string with timezone."""
        result = _parse_due_at("2026-05-01T23:59:00+00:00")
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_iso_with_z(self):
        """U39b: ISO string with Z suffix."""
        result = _parse_due_at("2026-05-01T23:59:00Z")
        assert result.tzinfo is not None

    def test_none_returns_none(self):
        """U39c: None input returns None."""
        assert _parse_due_at(None) is None


class TestCoerceMaxPoints:
    """Test U40: Max points validation."""

    def test_negative_raises(self):
        """U40a: Negative value raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            _coerce_max_points(-5)

    def test_zero_raises(self):
        """U40b: Zero raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            _coerce_max_points(0)

    def test_valid_float(self):
        """U40c: Valid numeric string is coerced."""
        assert _coerce_max_points("100") == 100.0


class TestValidatePayload:
    """Test U38: Assignment payload validation."""

    def test_empty_title_rejected(self):
        """U38: Empty title raises ValueError."""
        with pytest.raises(ValueError, match="title"):
            _validate_assignment_payload({"title": "", "instructions": "Do stuff", "max_points": 100})
\end{lstlisting}

\end{document}
