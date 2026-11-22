# AI Agent Instructions — Smart Laundromat Service Platform

## Project Overview

This is a university group project for EECS 4413, Fall 2026.

We are building a Smart Laundromat Service Platform where customers can register, browse washing machines and dryers, check availability, reserve time slots, complete simulated payments, and receive notifications.

Administrators can manage machines, reservations, payments, and view analytics.

The application must satisfy the course's revised project specification. Always consult the specification and existing project documentation before implementing a feature.

## Technology Stack

- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS
- Backend: Python 3.12, FastAPI
- Database: Supabase PostgreSQL
- Authentication: Supabase Auth
- Database access: Supabase Python SDK
- API style: REST with JSON
- Version control: Git and GitHub
- Architecture: Modular monolith with separate frontend and backend directories

Do not introduce another framework, ORM, database, or authentication provider without discussing it with the team.

## Repository Structure

```text
/
├── AGENTS.md
├── README.md
├── docs/
│   └── PROJECT_CONTEXT.md
├── frontend/
│   ├── app/
│   ├── lib/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   └── routers/
│   └── requirements.txt
└── supabase/
    └── migrations/
```

Some directories may not exist yet. Inspect the actual repository before making assumptions.

## Existing Implementation

The following functionality has been implemented and locally tested:

- FastAPI application and health endpoint
- Supabase database connection
- Machines table and machine-listing API
- Supabase Auth login
- Customer profiles with customer/admin roles
- FastAPI access-token verification
- Admin-only authorization test endpoint
- Next.js signup, login, and dashboard pages
- Logout functionality
- Basic homepage navigation

Do not assume additional functionality is complete without checking the code.

## Core Requirements

1. Customer registration, login, and profile management
2. Machine browsing, filtering, and availability
3. Time-slot reservations
4. Prevention of overlapping reservations under concurrent requests
5. Simulated payments with success/failure outcomes
6. Machine status simulation
7. Customer notifications
8. Admin machine, reservation, and payment management
9. Admin analytics dashboard
10. At least one AI/GenAI feature, such as natural-language machine availability search
11. Secure REST APIs and role-based authorization
12. Testing and at least one meaningful asynchronous/event-driven interaction

## Critical Architecture Rules

### Authentication and Authorization

- Supabase Auth manages passwords and sessions.
- The frontend sends Supabase access tokens to protected FastAPI endpoints.
- FastAPI validates tokens and enforces authorization.
- User roles are stored in the `profiles` table.
- New accounts must receive the `customer` role.
- Users must never be able to promote themselves to admin.
- Use user-scoped Supabase clients for protected database operations.
- Never expose secret or service-role keys in browser code.

### Reservations

Prevent overlapping bookings at the PostgreSQL level, not only through application checks.

Use a database-enforced exclusion constraint or equivalent concurrency-safe mechanism, together with an atomic booking operation.

Availability must account for machine status and existing reservations.

### Payments

Payments are simulated. Do not collect real payment-card details or introduce real charges.

### Backend

- Put business logic in FastAPI.
- Organize API endpoints using routers.
- Validate request data.
- Use meaningful HTTP status codes.
- Preserve existing API contracts unless a change is necessary.

### Frontend

- Use the existing Next.js App Router structure under `frontend/app/`.
- Use TypeScript and Tailwind CSS.
- Keep API calls and authentication logic reusable.
- Provide loading, error, and empty states.
- Do not treat hiding a UI element as sufficient authorization.

### Database

- Use PostgreSQL constraints and Row Level Security.
- Keep schema changes in version-controlled SQL migrations.
- Do not modify production-like or shared data destructively without approval.

## AI Agent Working Rules

Before making changes:

1. Read this file, `README.md`, and `docs/PROJECT_CONTEXT.md`.
2. Inspect the relevant existing code.
3. Identify which requirements your task addresses.
4. Explain your proposed changes briefly.
5. Avoid editing files owned by another teammate unless necessary.

While implementing:

- Prefer small, focused changes.
- Reuse existing patterns and dependencies.
- Avoid unnecessary refactoring.
- Do not fabricate working endpoints or database tables.
- Never commit credentials or environment files.
- Add tests for new backend behavior.
- Update documentation when introducing new configuration.

After implementing:

- Run relevant tests and lint checks.
- Report which files changed.
- Explain any database migrations.
- Document new environment variables.
- Identify unfinished work or known limitations.

## Collaboration

Each teammate should work on a separate Git branch and submit a pull request.

Avoid merging untested AI-generated code.

For shared files such as `backend/app/main.py`, database migrations, and common frontend components, coordinate changes before editing.

## Source of Truth

Priority order:

1. Revised EECS 4413 project specification
2. Team-approved architecture and decisions
3. Actual current repository implementation
4. This instruction file
5. Individual AI agent suggestions

If requirements conflict, raise the conflict instead of silently choosing an interpretation.