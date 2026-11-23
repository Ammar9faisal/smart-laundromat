# Smart Laundromat Service Platform

**EECS 4413 — Fall 2026**

A full-stack web application for managing laundromat machines, customer reservations, simulated payments, and administrative operations.

This project is being developed as a university group project.

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Next.js (App Router), React, TypeScript |
| Styling | Tailwind CSS |
| Backend | Python 3.12, FastAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Database Client | Supabase Python SDK |
| API Documentation | FastAPI Swagger/OpenAPI |
| Version Control | Git and GitHub |

## Prerequisites

Before starting, install:

- Git
- Node.js (LTS version) and npm
- Python 3.12
- VS Code (recommended)

You will also need access to our shared Supabase development project configuration.

## Getting Started

### 1. Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_FOLDER>
```

Replace the placeholders with the actual GitHub repository URL and folder name.

### 2. Configure Environment Variables

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Create `backend/.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_SECRET_KEY
```

The Supabase project URL and keys will be shared with team members.

| Variable | Used for |
|---|---|
| `SUPABASE_KEY` | The publishable key (`sb_publishable_...`). Used for public reads and, together with the user's access token, for everything a signed-in user does, so row level security applies. |
| `SUPABASE_SECRET_KEY` | The secret key (`sb_secret_...`). Backend only. Used solely to record payment outcomes, which customers must not be able to write themselves. Without it the rest of the API works and the payment endpoint returns 503. |
| `RESERVATION_HOLD_MINUTES` | Optional, default `15`. How long an unpaid reservation holds its slot. |

**Important:**
- `SUPABASE_KEY` must be the publishable key, not the secret key.
- The secret key belongs only in `backend/.env`, never in frontend code or `NEXT_PUBLIC_` variables.
- Do not commit `.env` or `.env.local` files.
- Do not use Supabase service-role or secret keys in frontend code.
- We use one shared Supabase development project, so teammates do not need to create separate databases.

### 3. Set Up the Backend

Open a terminal from the repository root:

```bash
cd backend
```

Create a Python virtual environment:

**macOS/Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Start FastAPI:

```bash
fastapi dev app/main.py
```

The backend should be available at:

- API: http://127.0.0.1:8000
- API Documentation: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

Keep this terminal running.

### 4. Set Up the Frontend

Open a **second terminal** from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

Both the frontend and backend must be running for the full application to work.

## Current Features

The following features have been implemented and tested during initial development:

| Feature | Status |
|---|---|
| Next.js frontend and homepage | Working |
| FastAPI backend | Working |
| Supabase database connection | Working |
| Customer signup | Working |
| Email/password login | Working |
| Logout | Working |
| Customer profiles | Working |
| Customer/admin role authorization | Working |
| Authenticated dashboard | Working |
| Machine listing REST API | Working |
| Machine browsing, filtering and availability (API and pages) | Working |
| Admin machine management: add, edit, change status, deactivate | Working |
| Reservations: create, list, view, cancel; overlap prevention | Working |
| Unpaid reservations expire and release their slot | Working |
| Simulated payments: success, decline, idempotency, refunds | Working |
| Admin dashboard: summary, machines, reservations, payments | Working (basic) |
| Backend unit tests (pytest) and Supabase integration tests | Working |
| Notifications | Not implemented |
| AI availability search | Not implemented |

This table reflects the initial implementation. Update it as features are merged.

## Application Pages

| URL | Description |
|---|---|
| `/` | Homepage |
| `/signup` | Customer registration |
| `/login` | User login |
| `/dashboard` | Authenticated user dashboard |
| `/machines` | Browse and filter machines; find a free machine for a time slot |
| `/machines/[id]` | Machine details, booked times for a day, reservation form |
| `/reservations` | The customer's reservations: pay with a test card or cancel |
| `/admin` | Administrators: summary, machine management, all reservations and payments |

## Backend API Endpoints

Full documentation (parameters, request and response bodies, status codes, access rules): [`docs/API.md`](docs/API.md). Interactive docs: http://127.0.0.1:8000/docs

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/health` | Public | Backend health check |
| GET | `/api/auth/me` | User | Authenticated user's profile |
| GET | `/api/auth/admin-test` | Admin | Test admin-only authorization |
| GET | `/api/machines/` | Public | Active machines (filters: `type`, `status`, `min_capacity`) |
| GET | `/api/machines/available` | Public | Machines free for a time window |
| GET | `/api/machines/{id}` | Public | Machine details |
| GET | `/api/machines/{id}/availability` | Public | Busy time ranges for a machine |
| POST | `/api/machines/` | Admin | Add a machine |
| PATCH | `/api/machines/{id}` | Admin | Update type, capacity, price or active flag |
| PATCH | `/api/machines/{id}/status` | Admin | Change machine status |
| DELETE | `/api/machines/{id}` | Admin | Deactivate a machine (soft delete) |
| POST | `/api/reservations` | User | Reserve a machine (409 if the slot overlaps) |
| GET | `/api/reservations` | User | Own reservations (admins: all) |
| GET | `/api/reservations/{id}` | User | One reservation |
| DELETE | `/api/reservations/{id}` | Owner/Admin | Cancel a reservation (refund if early) |
| POST | `/api/payments` | User | Pay with a test card (402 if declined) |
| GET | `/api/payments` | User | Own payments (admins: all) |
| GET | `/api/payments/{id}` | User | One payment |
| GET | `/api/admin/machines` | Admin | All machines, including inactive |
| GET | `/api/admin/summary` | Admin | Dashboard counts and revenue |

Protected endpoints require a valid Supabase access token in the `Authorization: Bearer <token>` header.

## Database

We use a shared Supabase PostgreSQL database.

### Existing Tables

**`machines`**

Stores machine information including type, capacity, price, status, and whether the machine is active.

**`profiles`**

Stores application user profiles linked to Supabase Auth users. Each user has a `customer` or `admin` role.

A database trigger automatically creates a customer profile when a new user registers.

### New Tables

These are defined in `supabase/migrations/` and have been applied to the shared project.

**`reservations`**

A customer's booking of one machine for a time slot. Overlapping active reservations for the same machine are rejected by a PostgreSQL exclusion constraint, so the rule holds under concurrent requests.

**`payments`**

Simulated payment attempts for a reservation, including failed attempts. No card details are stored.

Customers cannot write to either table directly. Bookings, cancellations and payments go through database functions (`create_reservation`, `cancel_reservation`, `record_payment`) that run each operation in a single transaction. See `docs/PROJECT_CONTEXT.md` for details.

### Migrations

| File | Purpose |
|---|---|
| `20261122170000_baseline_machines_profiles.sql` | Records the existing `machines` and `profiles` tables and signup trigger so the schema can be rebuilt from scratch. Guarded: existing tables, policies and the trigger are left as they are (it only turns on row level security if it is off). |
| `20261122170100_machine_profile_constraints.sql` | CHECK constraints on machine type/status and roles, the `is_admin()` helper, admin policies for machines, and stops customers from changing their own role. |
| `20261122170200_reservations_payments.sql` | `reservations` and `payments` tables, row level security, and the booking, cancellation, payment and availability functions. |

The shared project already has them. To set up another database (for example a local or test project), open the Supabase dashboard, go to **SQL Editor**, and run each file in order (oldest first).

To check the result, run `supabase/tests/reservation_rules_test.sql` in the SQL Editor afterwards. It creates its own test users and machines inside a transaction and rolls everything back at the end, so it leaves no data behind. Every check prints `PASS: ...`; the first failure stops the script with `FAIL: ...`.

### Database Changes

Coordinate schema changes with the team before modifying shared tables.

New tables, constraints, functions, and policies should be saved as SQL migration files in `supabase/migrations/` so the schema can be reproduced.

Do not delete shared tables or development data without discussing it with the team.

## Running Tests

Backend unit tests use pytest. They replace the Supabase clients with fakes, so they run offline and never touch the shared database.

From `backend/` with the virtual environment activated:

```bash
python -m pytest
```

Only the `backend/tests/` folder is collected (see `backend/pytest.ini`). `backend/test_login.py` is a manual helper for getting an access token and is not part of the test suite.

### Integration tests (real Supabase)

`backend/integration_tests/` runs the full booking and payment flow through the API against the shared Supabase project, including 50 simultaneous bookings for the same slot. The tests create two temporary users and a temporary machine and delete them, with everything they created, at the end. They need `SUPABASE_SECRET_KEY` in `backend/.env` and are skipped unless enabled:

```bash
RUN_INTEGRATION_TESTS=1 python -m pytest integration_tests
```

Database tests live in `supabase/tests/` (see the Migrations section above).

## Development Workflow

1. Pull the latest code from `main`.
2. Create a new branch for your feature.
3. Implement and test your changes locally.
4. Commit your changes.
5. Push your branch.
6. Open a pull request for review.

Example:

```bash
git checkout main
git pull origin main
git checkout -b feature/machine-browsing
```

After implementing your feature:

```bash
git add .
git commit -m "feat: implement machine browsing"
git push -u origin feature/machine-browsing
```

Create a pull request instead of directly pushing changes to `main`.

Coordinate changes to shared files, especially backend configuration, database migrations, and common frontend components.

## Working With AI Coding Agents

AI coding agents may be used to assist development.

Before asking an agent to implement a feature:

1. Have it inspect the existing repository.
2. Read `AGENTS.md` and `docs/PROJECT_CONTEXT.md` if those files are present.
3. Provide the revised EECS 4413 project specification.
4. Explain the assigned feature and its requirements.
5. Ask the agent to identify affected files, API contracts, and database changes before coding.

AI-generated code must be reviewed and tested before merging.

Avoid introducing new frameworks, authentication systems, or databases without team agreement.

## Planned Features

The remaining work includes:

- Machine browsing and availability filtering
- Reservation creation, viewing, and cancellation
- Database-enforced prevention of overlapping reservations
- Simulated payment success/failure
- Administrator machine and reservation management
- Machine status simulation
- Notifications and asynchronous/event-driven processing
- Analytics dashboard
- AI-powered natural-language availability search
- Automated testing

**Critical requirement:** Reservation conflicts must be prevented at the PostgreSQL level, including under concurrent booking requests.

## Troubleshooting

**Frontend does not start**

Run `npm install` inside `frontend/` and confirm Node.js is installed.

**Backend does not start**

Activate the Python virtual environment and install dependencies from `requirements.txt`.

**Supabase authentication fails**

Check that the frontend uses the correct Supabase URL and publishable key. Do not use a secret key in the browser.

**Frontend cannot connect to FastAPI**

Make sure the backend is running on port 8000 and `NEXT_PUBLIC_API_URL` is configured correctly.

**Machines are not appearing**

Test http://127.0.0.1:8000/api/machines/ directly. If it returns machine records, the backend connection works; check whether the frontend machine-browsing page has been implemented.

**Environment variables are not updating**

Restart the Next.js or FastAPI development server after changing environment files.

## Notes

- Supabase Auth handles user passwords and sessions.
- FastAPI handles protected business operations and authorization.
- Never commit credentials or access tokens.
- The backend currently uses FastAPI; confirm any required instructor approval for this framework under the revised course specification.
- Keep this README updated when new features or setup steps are introduced.