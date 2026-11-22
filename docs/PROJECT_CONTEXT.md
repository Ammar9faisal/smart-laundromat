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

Other tables, including reservations, payments, and notifications, still need to be designed and implemented.

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

Machine browsing UI and core reservation functionality are the next major development priorities.

Update this document as features are implemented.

## Important Course Constraint

The revised specification prefers Java/Spring Boot or an approved Java framework. Our team currently uses Python/FastAPI, so instructor approval must be confirmed.

Refer to the revised project specification for exact milestone requirements and grading criteria.