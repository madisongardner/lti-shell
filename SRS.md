

Software Requirements Specification
for
LTI-Shell Sandbox
Version 1.0 approved
Prepared by Cing Dim, Madison Gardner, Isaac Gentry
Western Kentucky University
01 February 2026

Table of Contents
1. Introduction	1
1.1 Purpose	1
1.2 Document Conventions	1
1.3 Project Scope	1
1.4 References	2
2. Overall Description	2
2.1 Product Perspective	2
2.2 User Classes and Characteristics	2
2.3 Operating Environment	3
2.4 Design and Implementation Constraints	3
2.5 Assumptions and Dependencies	3
3. System Features	4
3.1 LTI Launch and Role-Based Access Control	4
3.1.1 Description	4
3.1.2 Stimulus/Response Sequences	4
3.1.3 Functional Requirements	4
3.2 Instructor Assignment Management	5
3.2.2 Description	5
3.2.2 Stimulus/Response Sequences	5
3.2.3 Functional Requirements	5
3.3 Student Interactive Bash Environment	5
3.3.1 Description	5
3.3.2 Stimulus/Response Sequences	5
3.3.3 Functional Requirements	6
3.4 Instructor Assignment Management	6
3.4.1 Description	6
3.4.2 Stimulus/Response Sequences	6
3.4.3 Functional Requirements	6
3.5 Instructor Assignment Management	7
3.5.1 Description	7
3.5.2 Stimulus/Response Sequences	7
3.5.3 Functional Requirements	7
3.6 Instructor Assignment Management	7
3.6.1 Description	7
3.6.2 Stimulus/Response Sequences	7
3.6.3 Functional Requirements	8
4. Data Requirements	8
4.1 Logical Data Model	8
4.2 Data Dictionary	9
4.3 Reports	9
4.4 Data Acquisition, Integrity, Retention, and Disposal	9
5. External Interface Requirements	10
5.1 User Interfaces	10
5.2 Software Interfaces	10
5.3 Hardware Interfaces	11
5.4 Communications Interfaces	11
6. Quality Attributes	12
6.1 Usability	12
6.2 Performance	12
6.3 Security	12
6.4 Safety/Reliability	12
6.5 Scalability	13
7. Internationalization and Localization Requirements	13
8. Others	13
8.1 Deployment	13
8.2 Logging and Monitoring	13






Revision History
Name
Date
Reason For Changes
Version



















Name
Contribution
Isaac Gentry
Sections 4 and 5
Madison Gardner
Sections 1, 2, and 3
Cing Dim
Section 6, 7, 8









Introduction
This section provides an overview of the Software Requirements Specification (SRS) for the LTI-Shell system. It explains the purpose of the document, defines its intended audience, outlines conventions used throughout the specification, and establishes the scope of the project. The goal of this document is to clearly describe the functional and non-functional requirements of LTI-Shell so that stakeholders, developers, and evaluators share a common understanding of the system to be built and validated.
Purpose 
This Software Requirements Specification defines the requirements for the LTI-Shell. LTI-Shell is a web-based educational tool that integrates with Learning Management Systems (LMSs) using the LTI 1.3 standard to provide students with secure, interactive Linux Bash environments for coursework and automated assessment.
This document is intended for these audiences:
Developers, who will implement the system based on the specified requirements
Project stakeholders and instructors, who will use the system to create and manage assignments
Testers and evaluators, who will verify that the system meets its functional and quality requirements
Course staff and reviewers, who will assess the project as part of CS496
The SRS serves as the reference for what the system must do and the constraints under which it must operate.
Document Conventions
The following conventions are used throughout this document:
The term “shall” indicates a mandatory requirement that the system must satisfy.
The terms “should” and “may” indicate a recommended but non-mandatory requirement.
Section and subsection numbering follows the structure provided by the SRS template.
Functional requirements are clear to ensure they are verifiable and testable.
Project Scope
LTI-Shell is a standalone, web-based application designed to deliver interactive, command-line-based programming labs through integration with existing Learning Management Systems. The primary purpose of the system is to allow students to complete Bash-based assignments within a secure, disposable Linux environment without requiring local software installation or configuration.
The system supports the following high-level capabilities:
Integration with LMS platforms via the LTI 1.3 standard
Role-based identification of instructors and students through LMS launches
Instructor-managed assignment creation, including starter files and automated test scripts
Provisioning of isolated, ephemeral Linux containers for student assignment attempts
Automated execution of grading scripts and generation of feedback
Automatic grade passback to the LMS gradebook
LTI-Shell is designed to streamline instructional workflows, improve grading consistency, and enhance security by enforcing execution isolation. Features such as persistent environments, collaborative workspaces, support for non-Bash languages, and plagiarism detection are explicitly outside the scope of this release.
References
Learning Tools Interoperability (LTI) Core Specification 1.3, IMS Global Learning Consortium, 2019. https://www.imsglobal.org/spec/lti/v1p3/
LTI Assignment and Grade Services (AGS) Specification, IMS Global Learning Consortium, 2019. https://www.imsglobal.org/spec/lti-ags/v2p0/
Docker Documentation, Docker, Inc. https://docs.docker.com/
Overall Description
This section provides a high-level overview of the LTI-Shell system, including its context, intended users, operating environment, and known constraints, assumptions, and dependencies. It establishes how the system fits into the broader educational technology ecosystem and clarifies the conditions under which it is expected to operate.
Product Perspective
LTI-Shell is an entirely new software system designed to integrate with existing Learning Management Systems (LMSs) through the Learning Tools Interoperability (LTI) 1.3 standard. It is not a standalone course platform or a replacement for an LMS, but rather a complementary external tool that extends LMS functionality by providing secure, interactive command-line lab environments.
The system operates as an offering external to the LMS. Core LMS responsibilities such as user authentication, course enrollment, assignment visibility, and gradebook management remain under LMS control. LTI-Shell relies on LTI launch requests from the LMS to establish user identity, role, and assignment context, and communicates grades back to the LMS using LTI Assignment and Grade Services.
LTI-Shell is designed to be platform-agnostic and compatible with multiple LMS platforms. During development and testing, the system is intended to integrate with an open-source LMS (e.g., Moodle), while production deployment may target other LMS platforms such as Blackboard. Integration with different LMS platforms requires configuration changes only, so the core application logic remains unchanged.
User Classes and Characteristics
The LTI-Shell system supports the following user classes:
Instructor
Instructors use LTI-Shell to create and manage Bash-based assignments for their courses. They are responsible for defining assignment instructions, uploading starter files, and providing automated test scripts for grading. Instructors are expected to have basic familiarity with command-line environments and scripting but are not required to manage system infrastructure or container environments.
Student
Students access LTI-Shell through their course LMS to complete assigned labs. They interact with an in-browser Bash terminal to execute commands and modify files within an isolated environment. Students are not required to install or configure any local software. Skill levels may range from beginner to intermediate in command-line usage.
Administrator/config
Administrators are responsible for configuring LMS platform integrations and managing global system settings. This user class is considered optional and primarily relevant for system deployment and maintenance.
Operating Environment
LTI-Shell operates as a web-based application hosted on a Linux-based server environment. Users access the system through web browsers on desktop or laptop devices. No client-side software installation is required.
The system operates within the following environment:
Client Environment:
Web browsers (ex: Chrome)
Internet connection with HTTPS support
Server Environment:
Linux-based operating system
Container runtime environment (Docker) for sandbox execution
Web application framework and backend services
Integration Environment:
Learning Management Systems that support LTI 1.3 (e.g., Moodle, Blackboard)
Secure network communication between LMS and LTI-Shell
The system must coexist with institutional LMS platforms and adhere to their integration requirements without interfering with existing LMS functionality.
Design and Implementation Constraints
The following constraints limit the design and implementation options for LTI-Shell:
The system must comply with the LTI 1.3 standard for authentication, launch, and grade passback.
Assignment execution must occur within isolated Linux containers.
Containers must enforce resource limits, including CPU, memory, and execution time.
External network access from containers must be disabled by default.
The system supports Bash-based assignments only.
The system must integrate with LMS gradebooks exclusively through LTI services.
Persistent student environments across sessions are not supported.
Assumptions and Dependencies
The following assumptions and dependencies may affect the system’s requirements or behavior:
The LMS platform correctly implements the LTI 1.3 specification.
Users authenticate through the LMS prior to launching LTI-Shell.
The hosting environment provides sufficient resources to provision containers on demand.
Instructors provide valid starter files and test scripts, including a required run_tests.sh file.
The LMS gradebook service is available at the time of grade passback.
The container runtime and underlying operating system remain stable and supported throughout development and deployment.
System Features
This section describes the major functional features provided by the LTI-Shell system. Each feature represents a core service of the system and is described in terms of its purpose, stimulus/response sequences, and detailed functional requirements.
LTI Launch and Role-Based Access Control
Description
This feature enables secure access to LTI-Shell through an LMS using the LTI 1.3 standard. It validates LTI launch requests, identifies the user and their role (student or instructor), and provides access to the appropriate system interface.
Priority: High
Stimulus/Response Sequences
Stimulus: A user clicks an LTI-Shell assignment link within the LMS.
Response: The LMS initiates an LTI 1.3 launch request to LTI-Shell.
Stimulus: LTI-Shell receives the LTI launch request.
Response: The system validates the LTI ID token and verifies the request signature.
Stimulus: The launch request is successfully validated.
Response: The system extracts user identity, course context, assignment ID, and role information.
Stimulus: The user role is identified.
Response: If the user is an instructor, the Instructor Dashboard is displayed. If the user is a student, the Student Assignment interface is displayed.
Stimulus: The launch request is invalid or expired.
Response: The system denies access and displays an error message.
Functional Requirements
The system shall support LTI 1.3 launch requests from supported LMS platforms.
The system shall validate LTI ID tokens before granting access.
The system shall extract and store the user’s LMS identifier, course identifier, role, and assignment identifier from the launch request.
The system shall restrict access to instructor-only features based on LTI role claims.
The system shall deny access for invalid, expired, or malformed LTI launch requests.
The system shall display an appropriate error message when authentication or authorization fails.
Instructor Assignment Management
3.2.2	Description
This feature allows instructors to create and manage Bash-based assignments within LTI-Shell. Assignments include metadata, instructions, starter files, and automated test scripts that define grading behavior.
Priority: High
3.2.2	Stimulus/Response Sequences
Stimulus: An instructor launches LTI-Shell from the LMS.
Response: The system displays the Instructor Dashboard.
Stimulus: The instructor selects the option to create a new assignment.
Response: The system displays an assignment creation form.
Stimulus: The instructor submits assignment metadata and uploads starter and test files.
Response: The system validates the uploaded files and stores the assignment.
Stimulus: The assignment is successfully created.
Response: The system generates a unique Assignment ID and displays it to the instructor.
Stimulus: The instructor attempts to upload invalid or incomplete files.
Response: The system displays an error message and prevents assignment creation.
3.2.3	Functional Requirements
The system shall allow instructors to create new assignments through the Instructor Dashboard.
The system shall allow instructors to define assignment metadata, including title and instructions.
The system shall allow instructors to upload a ZIP archive containing starter files.
The system shall allow instructors to upload a ZIP archive containing automated test scripts, including a required run_tests.sh file.
The system shall validate uploaded files before accepting the assignment.
The system shall generate a unique Assignment ID for each assignment.
The system shall prevent students from accessing assignments that are not fully configured.
The system shall display clear error messages for invalid uploads or missing required files.
Student Interactive Bash Environment
Description
This feature provides students with an interactive Linux Bash environment for completing assignments. Each assignment attempt is executed within an isolated, disposable container that enforces resource and security constraints.
Priority: High
Stimulus/Response Sequences
Stimulus: A student launches an assignment from the LMS.
Response: The system validates the LTI launch and identifies the assignment.
Stimulus: The assignment launch is successful.
Response: The system provisions a new Linux container for the student’s assignment attempt.
Stimulus: The container is successfully initialized.
Response: The system displays the assignment instructions and an interactive Bash terminal to the student.
Stimulus: The student executes commands within the terminal.
Response: The system executes commands inside the isolated container and returns output to the user interface.
Stimulus: Container provisioning fails or exceeds resource limits.
Response: The system terminates the attempt and displays an error message to the student.
Functional Requirements
The system shall provision a new Linux container for each student assignment attempt.
The system shall provide students with an interactive Bash terminal connected to the container.
The system shall restrict container access to the assignment workspace only.
The system shall enforce resource limits, including CPU usage, memory usage, and execution time.
The system shall disable external network access from containers by default.
The system shall isolate each student’s container from all other users.
The system shall display an appropriate error message if the container cannot be created or started.
Assignment Submission, Automated Grading, and Feedback
3.4.1	Description
This feature enables students to submit completed assignments for automated grading. Upon submission, the system executes instructor-provided test scripts within the container, generates a numeric score, and displays feedback to the student.
Priority: High
3.4.2	Stimulus/Response Sequences
Stimulus: A student clicks the submit button within the assignment interface.
Response: The system locks the container workspace and initiates grading.
Stimulus: The grading process begins.
Response: The system executes the run_tests.sh script inside the container.
Stimulus: Test execution completes successfully.
Response: The system captures output, computes a numeric score, and generates feedback.
Stimulus: Test execution fails or exceeds execution limits.
Response: The system terminates the grading process and records the failure.
Stimulus: Grading results are available.
Response: The system displays feedback and score to the student.
3.4.3	Functional Requirements
The system shall allow students to submit an assignment for grading through the user interface.
The system shall execute instructor-provided test scripts within the student’s container upon submission.
The system shall enforce execution time limits during grading.
The system shall capture standard output and error output from test execution.
The system shall compute a numeric score based on test results.
The system shall display grading feedback to the student after submission.
The system shall terminate and clean up the container after grading is complete.
The system shall handle test execution failures gracefully and record appropriate error information.
Grade Passback to Learning Management System
3.5.1	Description
This feature enables LTI-Shell to communicate final assignment grades back to the LMS gradebook using LTI Assignment and Grade Services (AGS).
Priority: High
3.5.2	Stimulus/Response Sequences
Stimulus: Automated grading completes successfully.
Response: The system prepares the final score for grade passback.
Stimulus: The system sends the score to the LMS.
Response: The LMS acknowledges receipt of the grade.
Stimulus: Grade passback is successful.
Response: The system records the passback status and confirms submission to the student.
Stimulus: Grade passback fails due to a network or service error.
Response: The system records the failure and displays an appropriate message.
3.5.3	Functional Requirements
The system shall support LTI Assignment and Grade Services (AGS) for grade passback.
The system shall transmit numeric assignment scores to the LMS gradebook.
The system shall associate grades with the correct student, course, and assignment context.
The system shall confirm successful grade submission to the student.
The system shall record grade passback success or failure for auditing purposes.
The system shall handle temporary LMS communication failures gracefully.
Platform Configuration and Administration
3.6.1	Description
This feature provides administrative functionality for managing LMS platform integrations and system-wide configuration settings. This feature is considered optional and may be implemented if time permits.
Priority: Low
3.6.2	Stimulus/Response Sequences
Stimulus: An administrator accesses the system configuration interface.
Response: The system displays available platform and configuration settings.
Stimulus: The administrator updates LMS integration parameters.
Response: The system saves the updated configuration.
Stimulus: The administrator modifies sandbox resource limits.
Response: The system applies the updated limits to future containers.
3.6.3	Functional Requirements
The system may allow administrators to configure LMS platform integration settings.
The system may allow administrators to manage global sandbox resource limits.
The system may provide access to system logs for monitoring and debugging.
Data Requirements
This section addresses the data that will be dealt with during our LTI shell project. In these subsections we will address what the data specifically is, a logical representation of the system will manipulate the data, any reports that will be generated by the system and how we are going to maintain and keep all data secure.
Logical Data Model

   
     For teachers, we store basic account information, including their name and email address. To support LTI integration with Moodle, we also store their unique Moodle user ID and the Moodle server URL they authenticated. This allows our system to identify teachers when they launch our tool from Moodle and associate them with the courses and assignments they create.
     For students, we store the same basic account information as teachers: name, email, Moodle user ID, and Moodle server URL. This data is used to authenticate students when they access our system through Moodle and to track their assignment submissions and grades.
     For courses, we store the course name along with the LTI context ID provided by Moodle. The context ID allows our system to match courses between Moodle and our platform so that students and teachers see the correct course information when they launch our tool.
     For assignments, we store the title, instructions, due date, and maximum points. To enable grade passback, we also store two LTI-specific fields: the resource link ID, which identifies the specific assignment link in Moodle, and the lineitem URL, which is the endpoint our system uses to send grades back to Moodle.
     To communicate with Moodle, we store configuration data for each Moodle server that connects to our system. This includes the issuer URL, which identifies the Moodle server, our tool's registered client ID, and a deployment ID for the specific installation. We also store three authentication endpoints: the login URL for initiating authentication, the token URL for retrieving access tokens, and the JWKS URL, which provides the public keys needed to verify that LTI requests are authentic and have not been tampered with.

Data Dictionary
     The system manages data for two primary user types: Teachers and Students, both of which have user data such as passwords and usernames stored in our PostgreSQL server connected to Moodle. Teachers are associated with the courses they teach and the assignments they create. Students are enrolled in one or more courses and can view and complete assignments within those courses. Each Assignment contains a title, instructions, and a due date. When a student begins an assignment, a Docker Instance is created to provide them with an isolated Linux environment to complete their work. Once finished, the student creates a Submission, which records their work, and the Linux box is then graded using a different grading Linux container. Grades are then communicated back to Moodle via LTI integration.
Reports
      For this project, we did not plan on the integration of any sort of reporting functionality. If time allows, we may circle back to evaluate if we would like to add this functionality or not.  
Data Acquisition, Integrity, Retention, and Disposal
Data Acquisition
User data (teachers and students) is acquired when users register through Moodle. This includes their name, email, and password. When users access our LTI shell website, their identity is passed from Moodle via LTI authentication—no separate account creation is needed on our system.
Assignment data is created by teachers through the Moodle interface. Submission data is generated when students complete assignments in their Docker instances.
Data Storage & Security
All user credentials are stored in a PostgreSQL database. Passwords are encrypted before storage to protect user privacy.
Data Integrity
Regular database backups will be performed to prevent data loss
Grades are synced to Moodle via LTI to ensure consistency between systems
Temporary Data
Students will have Temporary docker instances created when doing assignments and data will be generated from these submissions. These containers will be terminated after the student submits their work or after a period of inactivity to free up server resources.

External Interface Requirements

User Interfaces
The system has two main user interfaces, with a potential third if time allows:
1. Student View
Upon login, students are presented with a dashboard displaying all courses they are enrolled in. After selecting a course, the student sees a list of available assignments. When an assignment is selected, a workspace opens containing:
A Linux command line terminal (connected to a freshly spawned Docker instance) on the left side of the screen
A submit button on the right side that sends the Docker instance for grading
2. Teacher View
Teachers have access to course and assignment management tools:
Course Creation – Teachers can create and manage their courses


Assignment Builder – A modular interface where teachers can construct assignments by selecting from multiple steps, each worth a configurable number of points. This allows teachers to build assignments piece by piece with flexible grading criteria.

3. Admin View (If Time Allows)
An administrative interface that allows users with admin privileges to:
Edit backend settings for the LTI shell website
Manage system configuration
Admin view will be per-configured LMS
Can allow for multiple LMS systems that support LTI 1.3

Software Interfaces
     Moodle LMS serves as the central hub for user management, course enrollment, and grade storage. Our system communicates with Moodle using the LTI (Learning Tools Interoperability) protocol. When a user launches an assignment, Moodle sends user identity and course context to our LTI shell website. When a student completes an assignment, our system sends the grade back to Moodle.
     PostgreSQL is used as the database for persistent storage of all system data. This includes user information with encrypted credentials, course and assignment data, and submission records with grades.
     Docker provides isolated Linux environments for student assignments. Our system communicates with Docker through its API to create, start, and terminate containers. Docker returns container status and connection information, and student terminal input and output is streamed between the browser and the container in real time.

Hardware Interfaces
     Users only require a web browser and an internet connection to access our system. There are no special hardware requirements for students or teachers.
     The primary hardware interface is the communication between the user's device and our web server. The user's browser sends HTTP/HTTPS requests to our server, which responds with web pages, assignment data, and terminal output. This communication uses standard web protocols and is compatible with any modern web browser on desktop or mobile devices.
     For the terminal interface, the user's keyboard input is captured by the browser and transmitted to the Docker container via websockets. The container's output is then streamed back to the browser and displayed in real time. This requires a stable internet connection to ensure smooth interaction with the Linux environment.

Communications Interfaces
Our system relies on several communication protocols to connect users, our web server, and Moodle.
HTTPS is used for all standard web traffic between the user's browser and our server. This includes loading pages, retrieving assignment data, and submitting forms. All traffic is encrypted to protect user data in transit.
Websockets provide a persistent, real-time connection between the user's browser and their Docker container. This is necessary for the terminal interface, where keystrokes must be sent instantly and output displayed without delay. We will use xterm.js on the frontend to render the terminal and communicate over websockets to stream input and output to and from the Docker container.
LTI (Learning Tools Interoperability) handles authentication and data exchange with Moodle. When a user accesses our website, LTI verifies their identity through Moodle and provides user and course information. When a student completes an assignment, LTI is used to send the grade back to Moodle. All LTI communication is secured using OAuth signatures to ensure requests are authentic and have not been tampered with.
The Docker API is used internally by our server to manage containers. This includes creating new instances when students start assignments, monitoring container status, and terminating containers after submission or inactivity.

Quality Attributes
Usability
The system will prioritize ease of use and minimal setup for both students and instructors. The goal is for LTI-Shell to be usable without any prior configuration or installation needed. 
Requirements for the software to appear to be “user-friendly”
The system will operate entirely within a web browser with no installation required. 
There is a clear separation between student and instructor interfaces
The system will display assignment instructions and terminal in the same view. 
If there are any failed launches, container failures, or grading errors, there will be clear error messages.
Students should be able to begin an assignment within less than three clicks.
The system support keyboard only navigation
Have responsive layouts for common screen size(≥ 1280px width)
Performance
The student containers open within 5 seconds under normal load.
Support at least 30 concurrent student containers without degradation
Terminal command latency not exceed 200ms round-trip under normal network conditions. 
Student containers shall automatically terminate after 15 minutes of inactivity or at assignment end.
The system shall automatically queue or throttle new container requests when capacity limits are reached.
Security
The system shall authenticate all students and instructors users through LTI 1.3 authentication.
The system shall have a low priority admin.
The system shall use HTTPS for all communications.
Each student assignment shall run inside an isolated container.
Containers shall have:
no privileged mode
limited CPU and memory
disabled outbound network access
The system shall sanitize all uploaded instructor files.
The system shall log authentication events and grading actions.
The system shall prevent students from accessing other students’ data.
The system shall automatically delete containers after grading or session expiration.
Safety/Reliability 
The system shall achieve 99% uptime during academic hours.
The system shall automatically restart failed containers.
The system shall retry grade passback up to 3 times upon failure.
System logs shall capture all failures for debugging.

Scalability
The system shall support horizontal scaling to allow increased numbers of users and container launches. 
The system shall support adding more servers to handle increased usage.
The system shall place container requests into a queue and allow worker servers to process them gradually to prevent overload.
Internationalization and Localization Requirements
The system shall support UTF-8 character encoding.
The system shall format dates and times according to the LMS locale.
The system shall ship with English only
Others
Deployment
The system shall use Docker Compose to orchestrate all required application services.
The system shall support automated build and deployment pipelines using GitHub Actions.
The system shall support configuration via environment variables without code modifications.
 Logging and Monitoring
The system shall log
LTI launches
Container creation/destruction
Grading events
Grade passback attempts
System errors
Logs include timestamps and user id



Appendix A: Glossary

Term
Definition
LTI
Learning Tools Interoperability standard for LMS integrations
LMS
Learning Management System
Container
Isolated runtime environment used for executing assignments
Sandbox
Restricted environment preventing unauthorized access
Grade Passback
Process of sending grades to LMS


AGS
Assignment and Grade Services (LTI component)
Ephemeral
Temporary; destroyed after use
Instructor Dashboard
Interface for creating assignments/ assigning assignments
Student Workspace
Terminal environment for assignment completion


Appendix B: Analysis Models
<This optional section includes or points to pertinent analysis models such as data flow diagrams, feature trees, state-transition diagrams, or entity-relationship diagrams. You might prefer to insert certain models into the relevant sections of the specification instead of collecting them at the end.>
