# Smart Laundromat — Project Context

## Project Goal

Build a web-based laundromat management and reservation platform that allows customers to book washers and dryers while providing administrators with machine management and operational tools.

## Architecture

The application has three primary layers:

**Frontend — Next.js**

Handles customer and administrator interfaces, navigation, forms, and session management.

**Backend — FastAPI**

Handles business logic, REST endpoints, authorization, reservations, payments, analytics, and AI integration.

**Supabase — PostgreSQL and Auth**

Provides persistent relational storage, authentication, Row Level Security, and database constraints.

## Current Database

### machines

Existing fields:

- `id` — machine identifier
- `type` — WASHER or DRYER
- `capacity` — machine capacity
- `price` — machine price
- `status` — machine operational status
- `active` — whether the machine is active

### profiles

Existing fields:

- `id` — UUID referencing Supabase Auth user
- `full_name` — customer's name
- `role` — customer or admin
- `created_at` — creation timestamp

A database trigger creates customer profiles when users register.

Customers may update their own `full_name` but never their `role` (enforced with column privileges).

### reservations

- `id`, `user_id` (profile), `machine_id`
- `start_time`, `end_time` — stored as `timestamptz` (UTC)
- `status` — PENDING_PAYMENT, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, EXPIRED
- `price` — copied from the machine when the reservation is created
- `expires_at` — when an unpaid reservation stops holding its slot (15 minutes by default)
- `version`, `created_at`, `updated_at`

The `reservations_no_overlap` exclusion constraint rejects two PENDING_PAYMENT, CONFIRMED or IN_PROGRESS reservations for the same machine whose times overlap. A booking may start exactly when another ends.

### payments

- `id`, `reservation_id`, `user_id`
- `amount`, `currency` (default CAD)
- `status` — PENDING, SUCCEEDED, FAILED, REFUNDED
- `provider` (SIMULATED), `provider_ref`, `failure_reason`
- `idempotency_key` — unique per user; repeating a request returns the original payment

A reservation can have at most one SUCCEEDED/REFUNDED payment. Failed attempts are kept.

### Database functions

Customers have read-only access to their own reservations and payments (admins can read all). Every change goes through these functions, which take the user from the access token and run in a single transaction:

| Function | Called by | Purpose |
|---|---|---|
| `create_reservation(machine_id, start_time, end_time, hold_minutes = 15)` | user-scoped client | Validates times and machine status, releases lapsed unpaid holds, inserts a PENDING_PAYMENT reservation |
| `cancel_reservation(reservation_id)` | user-scoped client | Owner or admin cancels a future reservation; refunds a successful payment if more than 15 minutes before the start |
| `record_payment(user_id, reservation_id, succeeded, provider_ref, failure_reason, idempotency_key, currency)` | **service role only** | Stores a payment outcome; success confirms the reservation, failure leaves it PENDING_PAYMENT |
| `expire_stale_reservations()` | service role only | Marks all lapsed unpaid reservations EXPIRED (for a scheduled job or the simulator) |
| `get_machine_busy_slots(machine_id, from, to)` | anyone | Busy time ranges for one machine (max 31-day window), without exposing who booked them |
| `get_available_machines(start_time, end_time, type = null)` | anyone | Active, in-service machines with no booking in the window |

Call them from FastAPI with `client.rpc("create_reservation", {"p_machine_id": ..., ...})`.

`record_payment` is restricted to the service role so a customer cannot mark their own reservation as paid by calling the database API directly. The payments endpoint therefore uses a server-side client created with the Supabase secret key (`SUPABASE_SECRET_KEY` in `backend/.env`; never in frontend code). All other endpoints use the publishable key with the caller's access token.

Errors raised by the functions, and the HTTP status the API should return:

| SQLSTATE | Meaning | HTTP |
|---|---|---|
| `28000` | Not signed in | 401 |
| `P0002` | Machine or reservation not found (or belongs to someone else) | 404 |
| `22023` | Invalid input, e.g. start time in the past or end before start | 422 |
| `LM001` | Machine inactive or out of service | 422 |
| `23P01` | Time slot overlaps another active reservation | 409 |
| `LM002` | Reservation is in a state that does not allow the action (already paid, already cancelled, hold expired, already started) | 409 |

Notifications are still to be designed (Milestone 3).

## Current API Endpoints

See [`API.md`](API.md) for the full list with request/response bodies and status codes. Summary:

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth | `GET /api/auth/me`, `GET /api/auth/admin-test` |
| Machines (public) | `GET /api/machines/`, `GET /api/machines/available`, `GET /api/machines/{id}`, `GET /api/machines/{id}/availability` |
| Machines (admin) | `POST /api/machines/`, `PATCH /api/machines/{id}`, `PATCH /api/machines/{id}/status`, `DELETE /api/machines/{id}` |
| Reservations | `POST /api/reservations`, `GET /api/reservations`, `GET /api/reservations/{id}`, `DELETE /api/reservations/{id}` |
| Payments | `POST /api/payments`, `GET /api/payments`, `GET /api/payments/{id}` |
| Admin | `GET /api/admin/machines`, `GET /api/admin/summary` |

Backend layout:

- `app/routers/` — one router per area (HTTP only)
- `app/schemas/` — Pydantic request/response models and booking rules
- `app/services/payment_gateway.py` — simulated payment gateway (Stripe-style test payment methods), replaceable through a FastAPI dependency
- `app/errors.py` — maps database error codes to HTTP status codes
- `app/dependencies.py` — authentication, admin check, and the Supabase client for each request (user-scoped, admin, or the secret-key service client for payments)

Verify these endpoints against the repository before changing them.

## Current Frontend Routes

| Route | Purpose |
|---|---|
| `/` | Homepage |
| `/signup` | Customer registration |
| `/login` | User login |
| `/dashboard` | Authenticated profile/dashboard |
| `/machines` | Browse/filter machines, find a free machine for a time slot |
| `/machines/[id]` | Machine details, busy times for a day, reservation form |
| `/reservations` | Customer's reservations: pay with a test card, cancel |
| `/admin` | Admin summary, machine management, all reservations and payments |

Shared frontend code: `lib/api.ts` (calls FastAPI with the user's access token and turns errors into messages), `lib/types.ts`, `lib/format.ts`, `components/AppNav.tsx`.

## Features Still to Implement

Machine browsing, reservations, simulated payments and a basic admin dashboard are implemented (Milestone 2). Remaining:

### Machine Simulation

Simulate machine transitions such as available, reserved, in use, and out of service.

### Notifications

Notify customers about meaningful reservation or machine events. Implement a meaningful asynchronous/event-driven interaction.

### AI Feature

Implement natural-language availability search. For example:

"Find an available washer with at least 10 kg capacity tomorrow afternoon."

The AI should interpret the request and use real application availability data. It must not invent machine availability.

## Security Requirements

- All protected requests require valid Supabase authentication.
- Customer data must be restricted to its owner.
- Admin actions require backend authorization.
- PostgreSQL RLS must be configured appropriately.
- Never trust frontend-provided user IDs or roles.
- Do not store real payment-card data.

## Testing Expectations

Test authentication, role restrictions, machine APIs, reservation conflicts, concurrent booking attempts, simulated payments, and critical frontend workflows.

## Development Status

Initial authentication and backend connectivity are working.

Milestone 2 features are implemented: machine browsing and availability, admin machine management, reservations with database-enforced overlap prevention, unpaid-reservation expiry, simulated payments (success, decline, idempotency, refunds) and a basic admin dashboard.

The database layer was tested against a local PostgreSQL database (all checks in `supabase/tests/reservation_rules_test.sql` pass; 50 simultaneous bookings for the same slot produced exactly one reservation). The migrations are applied to the shared Supabase project, and the integration tests pass against it, including 50 simultaneous bookings through the API.

Backend unit tests run with `python -m pytest` from `backend/`; integration tests against Supabase with `RUN_INTEGRATION_TESTS=1 python -m pytest integration_tests`.

Next (Milestone 3): notifications through an event-driven/asynchronous flow, machine status simulation, analytics, containerization and deployment, and the AI availability assistant.

Update this document as features are implemented.

## Important Course Constraint

The revised specification prefers Java/Spring Boot or an approved Java framework. Our team currently uses Python/FastAPI, so instructor approval must be confirmed.

Refer to the revised project specification for exact milestone requirements and grading criteria.