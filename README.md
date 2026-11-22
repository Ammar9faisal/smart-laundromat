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
```

The Supabase project URL and publishable key will be shared with team members.

**Important:**
- Use the publishable key (`sb_publishable_...`), not the secret key.
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
| Machine browsing frontend | Not yet confirmed complete |
| Reservation system | Not implemented |
| Simulated payments | Not implemented |
| Notifications | Not implemented |
| Admin management dashboard | Not implemented |
| AI availability search | Not implemented |

This table reflects the initial implementation. Update it as features are merged.

## Application Pages

| URL | Description |
|---|---|
| `/` | Homepage |
| `/signup` | Customer registration |
| `/login` | User login |
| `/dashboard` | Authenticated user dashboard |

Machine browsing UI is planned at `/machines`.

## Backend API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Backend health check |
| GET | `/api/machines/` | Retrieve active machines |
| GET | `/api/auth/me` | Retrieve authenticated user's profile |
| GET | `/api/auth/admin-test` | Test admin-only authorization |

Protected endpoints require a valid Supabase access token in the `Authorization: Bearer <token>` header.

Additional endpoints will be introduced as development continues.

## Database

We use a shared Supabase PostgreSQL database.

### Existing Tables

**`machines`**

Stores machine information including type, capacity, price, status, and whether the machine is active.

**`profiles`**

Stores application user profiles linked to Supabase Auth users. Each user has a `customer` or `admin` role.

A database trigger automatically creates a customer profile when a new user registers.

### Database Changes

Coordinate schema changes with the team before modifying shared tables.

New tables, constraints, functions, and policies should be saved as SQL migration files in `supabase/migrations/` so the schema can be reproduced.

Do not delete shared tables or development data without discussing it with the team.

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