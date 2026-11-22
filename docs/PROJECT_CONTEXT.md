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

### reservations (migration pending review)

- `id`, `user_id` (profile), `machine_id`
- `start_time`, `end_time` — stored as `timestamptz` (UTC)
- `status` — PENDING_PAYMENT, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, EXPIRED
- `price` — copied from the machine when the reservation is created
- `expires_at` — when an unpaid reservation stops holding its slot (15 minutes by default)
- `version`, `created_at`, `updated_at`

The `reservations_no_overlap` exclusion constraint rejects two PENDING_PAYMENT, CONFIRMED or IN_PROGRESS reservations for the same machine whose times overlap. A booking may start exactly when another ends.

### payments (migration pending review)

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

`record_payment` is restricted to the service role so a customer cannot mark their own reservation as paid by calling the database API directly. The payments endpoint will therefore need a server-side client created with the Supabase secret key (planned as a separate `SUPABASE_SECRET_KEY` variable in `backend/.env`; never in frontend code).

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

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health check |
| GET | `/api/machines/` | List active machines |
| GET | `/api/auth/me` | Get authenticated user profile |
| GET | `/api/auth/admin-test` | Verify admin authorization |

Verify these endpoints against the repository before changing them.

## Current Frontend Routes

| Route | Purpose |
|---|---|
| `/` | Homepage |
| `/signup` | Customer registration |
| `/login` | User login |
| `/dashboard` | Authenticated profile/dashboard |
| `/machines` | Machine browsing — planned or in progress |

## Features Still to Implement

### Machine Browsing

Display real machine data from FastAPI. Add filters for machine type, capacity, and availability.

### Reservations

Customers should be able to select a machine, date, and time slot, create reservations, and view or cancel their bookings.

Overlapping active reservations for the same machine must be rejected even under simultaneous requests.

### Simulated Payments

Create payment records associated with reservations. Support simulated success and failure, with consistent reservation/payment states.

### Admin Dashboard

Administrators should be able to create, update, disable, and inspect machines; manage reservations; inspect payments; and view operational analytics.

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

The reservation and payment database layer is written and tested against a local PostgreSQL database (all checks in `supabase/tests/reservation_rules_test.sql` pass; 50 simultaneous bookings for the same slot produced exactly one reservation). It has not been applied to the shared project yet.

Backend unit tests run with `python -m pytest` from `backend/`.

Machine browsing UI and the reservation and payment API endpoints are the next major development priorities.

Update this document as features are implemented.

## Important Course Constraint

The revised specification prefers Java/Spring Boot or an approved Java framework. Our team currently uses Python/FastAPI, so instructor approval must be confirmed.

Refer to the revised project specification for exact milestone requirements and grading criteria.