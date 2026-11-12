# Smart Laundromat Service Platform

EECS 4413 – Fall 2026

A web application for browsing laundromat machines, making reservations, processing simulated payments, and managing machine availability.

## Tech Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **Database:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth

## Prerequisites

Install the following before getting started:

- Node.js (LTS version)
- Python 3.12
- Git

## 1. Clone the Repository

```bash
git clone <repository-url>
cd smart-laundromat
```

Replace `<repository-url>` with our GitHub repository URL.

## 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
npm install
```

Create a `.env.local` file inside `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<supabase-publishable-key>
```

Get the Supabase project URL and publishable key from the shared project configuration.

Start the frontend:

```bash
npm run dev
```

Frontend: http://localhost:3000

## 3. Backend Setup

Open a second terminal and navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python3.12 -m venv .venv
```

Activate the environment.

**macOS/Linux:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```env
SUPABASE_URL=<supabase-project-url>
SUPABASE_KEY=<supabase-publishable-key>
```

Start FastAPI:

```bash
fastapi dev app/main.py
```

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

## 4. Supabase Setup

The team uses one shared Supabase development project.

1. Obtain the project URL and publishable key from the team.
2. Add these values to the frontend and backend environment files.
3. The database tables and sample data are managed through the shared Supabase project.

**Do not commit `.env` or `.env.local` files to GitHub. Never expose Supabase secret or service-role keys in frontend code.**

## 5. Running the Application

Both servers must be running simultaneously.

**Terminal 1 — Frontend**

```bash
cd frontend
npm run dev
```

**Terminal 2 — Backend**

```bash
cd backend
source .venv/bin/activate
fastapi dev app/main.py
```

On Windows, use the PowerShell activation command from Section 3.

Open http://localhost:3000 to access the application.

To verify the backend, visit:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/machines/

## 6. Git Workflow

Create a separate branch for your assigned feature:

```bash
git checkout -b feature/your-feature-name
```

After making changes:

```bash
git add .
git commit -m "Describe your changes"
git push -u origin feature/your-feature-name
```

Create a pull request on GitHub for another team member to review before merging into `main`.

Before starting new work, pull the latest changes from `main`.

## 7. Current Development Status

The project is in its initial development stage.

The initial setup includes:

- Next.js frontend
- FastAPI backend
- Supabase connection configuration
- Initial machine API

Upcoming features include authentication, reservations, simulated payments, machine management, notifications, analytics, and AI integration.

## Troubleshooting

**Frontend dependencies missing:** Run `npm install` inside `frontend/`.

**Backend dependencies missing:** Activate `.venv` and run `python -m pip install -r requirements.txt`.

**Supabase connection errors:** Check that your environment variables contain the correct project URL and publishable key.

**Frontend cannot reach backend:** Make sure FastAPI is running on port 8000 and `NEXT_PUBLIC_API_URL` is configured correctly.

**Environment variables not updating:** Restart the relevant development server.