-- Reservations and payments
--
-- Requirements covered: FR-12 to FR-22, NF-3, NF-4, NF-11.
--
-- Design notes
-- * Overlapping bookings are rejected by an exclusion constraint, so the rule
--   holds even when two requests arrive at the same moment (NF-3). The
--   application does not need to check for overlaps first.
-- * Customers cannot write to these tables directly. All changes go through
--   the functions below, which run each operation in a single transaction and
--   always take the user id from the access token (auth.uid()), never from the
--   request.
-- * record_payment() can only be executed by the backend's service role, so a
--   customer cannot mark their own reservation as paid by calling the database
--   API directly.
--
-- Error codes raised by the functions (mapped to HTTP status codes by FastAPI):
--   28000  not signed in                                   -> 401
--   P0002  machine / reservation not found or not yours    -> 404
--   22023  invalid input (times, hold period)              -> 422
--   LM001  machine is inactive or out of service           -> 422
--   23P01  time slot overlaps another active reservation   -> 409
--   LM002  reservation is not in a state that allows this  -> 409

create extension if not exists btree_gist with schema extensions;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------
create table public.reservations (
    id bigint generated always as identity primary key,
    user_id uuid not null references public.profiles (id) on delete cascade,
    machine_id bigint not null references public.machines (id) on delete restrict,
    start_time timestamptz not null,
    end_time timestamptz not null,
    status text not null default 'PENDING_PAYMENT',
    price numeric(10, 2) not null,
    expires_at timestamptz,
    version integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint reservations_status_check check (
        status in ('PENDING_PAYMENT', 'CONFIRMED', 'IN_PROGRESS',
                   'COMPLETED', 'CANCELLED', 'EXPIRED')
    ),
    constraint reservations_time_order_check check (end_time > start_time),
    constraint reservations_price_check check (price >= 0),
    constraint reservations_pending_expiry_check check (
        status <> 'PENDING_PAYMENT' or expires_at is not null
    ),
    -- Two active reservations for the same machine may not share any time.
    -- '[)' bounds let one booking end exactly when the next one starts.
    constraint reservations_no_overlap exclude using gist (
        machine_id with =,
        tstzrange(start_time, end_time, '[)') with &&
    ) where (status in ('PENDING_PAYMENT', 'CONFIRMED', 'IN_PROGRESS'))
);

comment on column public.reservations.expires_at is
    'When an unpaid (PENDING_PAYMENT) reservation stops holding its time slot.';
comment on column public.reservations.version is
    'Incremented on every update; available for optimistic locking.';

create index reservations_user_start_idx
    on public.reservations (user_id, start_time desc);
create index reservations_machine_start_idx
    on public.reservations (machine_id, start_time);
create index reservations_pending_expiry_idx
    on public.reservations (expires_at)
    where status = 'PENDING_PAYMENT';

create table public.payments (
    id bigint generated always as identity primary key,
    reservation_id bigint not null references public.reservations (id) on delete cascade,
    user_id uuid not null references public.profiles (id) on delete cascade,
    amount numeric(10, 2) not null,
    currency text not null default 'CAD',
    status text not null,
    provider text not null default 'SIMULATED',
    provider_ref text,
    failure_reason text,
    idempotency_key text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint payments_status_check check (
        status in ('PENDING', 'SUCCEEDED', 'FAILED', 'REFUNDED')
    ),
    constraint payments_amount_check check (amount >= 0),
    constraint payments_currency_check check (currency ~ '^[A-Z]{3}$'),
    constraint payments_idempotency_key_length_check check (
        idempotency_key is null or char_length(idempotency_key) between 8 and 100
    )
);

-- A reservation can be charged successfully at most once.
create unique index payments_one_success_per_reservation
    on public.payments (reservation_id)
    where status in ('SUCCEEDED', 'REFUNDED');
-- Repeating a request with the same idempotency key never creates a second
-- payment (FR-21).
create unique index payments_user_idempotency_key_idx
    on public.payments (user_id, idempotency_key)
    where idempotency_key is not null;
create index payments_reservation_idx on public.payments (reservation_id);
create index payments_user_created_idx on public.payments (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- updated_at / version bookkeeping
-- ---------------------------------------------------------------------------
create or replace function public.touch_row()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := now();
    if tg_table_name = 'reservations' then
        new.version := old.version + 1;
    end if;
    return new;
end;
$$;

create trigger reservations_touch_row
    before update on public.reservations
    for each row execute function public.touch_row();

create trigger payments_touch_row
    before update on public.payments
    for each row execute function public.touch_row();

-- ---------------------------------------------------------------------------
-- Row level security
-- ---------------------------------------------------------------------------
alter table public.reservations enable row level security;
alter table public.payments enable row level security;

revoke all on public.reservations, public.payments from anon;
revoke insert, update, delete, truncate on public.reservations, public.payments
    from authenticated;

create policy "Customers can view own reservations"
    on public.reservations
    for select
    to authenticated
    using (user_id = (select auth.uid()));

create policy "Admins can view all reservations"
    on public.reservations
    for select
    to authenticated
    using ((select public.is_admin()));

create policy "Customers can view own payments"
    on public.payments
    for select
    to authenticated
    using (user_id = (select auth.uid()));

create policy "Admins can view all payments"
    on public.payments
    for select
    to authenticated
    using ((select public.is_admin()));

-- ---------------------------------------------------------------------------
-- create_reservation: atomic booking (FR-12, FR-13, FR-16, FR-17)
-- ---------------------------------------------------------------------------
create or replace function public.create_reservation(
    p_machine_id bigint,
    p_start_time timestamptz,
    p_end_time timestamptz,
    p_hold_minutes integer default 15
)
returns public.reservations
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_machine public.machines;
    v_reservation public.reservations;
begin
    if v_user_id is null then
        raise exception 'Sign in to make a reservation' using errcode = '28000';
    end if;

    if p_start_time is null or p_end_time is null or p_end_time <= p_start_time then
        raise exception 'End time must be after start time' using errcode = '22023';
    end if;

    if p_start_time <= now() then
        raise exception 'Reservations cannot start in the past' using errcode = '22023';
    end if;

    if p_hold_minutes is null or p_hold_minutes not between 1 and 60 then
        raise exception 'Hold period must be between 1 and 60 minutes'
            using errcode = '22023';
    end if;

    -- FOR SHARE: concurrent bookings can still proceed, but an administrator
    -- cannot take the machine out of service until this transaction finishes.
    select * into v_machine
    from public.machines
    where id = p_machine_id
    for share;

    if not found then
        raise exception 'Machine % not found', p_machine_id using errcode = 'P0002';
    end if;

    if not v_machine.active or v_machine.status = 'OUT_OF_SERVICE' then
        raise exception 'Machine % is not available for reservations', p_machine_id
            using errcode = 'LM001';
    end if;

    -- Unpaid reservations whose hold has run out no longer block the slot.
    update public.reservations
    set status = 'EXPIRED'
    where machine_id = p_machine_id
      and status = 'PENDING_PAYMENT'
      and expires_at <= now();

    begin
        insert into public.reservations (
            user_id, machine_id, start_time, end_time, status, price, expires_at
        )
        values (
            v_user_id, p_machine_id, p_start_time, p_end_time, 'PENDING_PAYMENT',
            v_machine.price, now() + make_interval(mins => p_hold_minutes)
        )
        returning * into v_reservation;
    exception
        when exclusion_violation then
            raise exception 'Machine % is already reserved for part of that time',
                p_machine_id using errcode = '23P01';
    end;

    return v_reservation;
end;
$$;

-- ---------------------------------------------------------------------------
-- cancel_reservation: owner or admin cancels a future reservation (FR-15).
-- A successful payment is refunded when the cancellation happens more than
-- 15 minutes before the start time (FR-19).
-- ---------------------------------------------------------------------------
create or replace function public.cancel_reservation(p_reservation_id bigint)
returns public.reservations
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_reservation public.reservations;
begin
    if v_user_id is null then
        raise exception 'Sign in to cancel a reservation' using errcode = '28000';
    end if;

    select * into v_reservation
    from public.reservations
    where id = p_reservation_id
    for update;

    -- Someone else's reservation is reported as not found so its existence
    -- is not revealed.
    if not found or (v_reservation.user_id <> v_user_id and not public.is_admin()) then
        raise exception 'Reservation % not found', p_reservation_id using errcode = 'P0002';
    end if;

    if v_reservation.status not in ('PENDING_PAYMENT', 'CONFIRMED') then
        raise exception 'A % reservation cannot be cancelled', lower(v_reservation.status)
            using errcode = 'LM002';
    end if;

    if v_reservation.start_time <= now() then
        raise exception 'Reservations that have already started cannot be cancelled'
            using errcode = 'LM002';
    end if;

    update public.reservations
    set status = 'CANCELLED'
    where id = p_reservation_id
    returning * into v_reservation;

    if v_reservation.start_time > now() + interval '15 minutes' then
        update public.payments
        set status = 'REFUNDED'
        where reservation_id = p_reservation_id
          and status = 'SUCCEEDED';
    end if;

    return v_reservation;
end;
$$;

-- ---------------------------------------------------------------------------
-- record_payment: stores the outcome of a simulated payment and confirms the
-- reservation in the same transaction (FR-18 to FR-21, NF-4).
--
-- Called by the backend after its payment gateway (simulated) has decided the
-- outcome. Only the service role may execute it.
-- ---------------------------------------------------------------------------
create or replace function public.record_payment(
    p_user_id uuid,
    p_reservation_id bigint,
    p_succeeded boolean,
    p_provider_ref text default null,
    p_failure_reason text default null,
    p_idempotency_key text default null,
    p_currency text default 'CAD'
)
returns public.payments
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_reservation public.reservations;
    v_payment public.payments;
begin
    if p_user_id is null or p_reservation_id is null or p_succeeded is null then
        raise exception 'User, reservation and outcome are required' using errcode = '22023';
    end if;

    -- Lock the reservation first so concurrent attempts for it run one at a time.
    select * into v_reservation
    from public.reservations
    where id = p_reservation_id
    for update;

    if not found or v_reservation.user_id <> p_user_id then
        raise exception 'Reservation % not found', p_reservation_id using errcode = 'P0002';
    end if;

    -- A repeated request returns the payment that was already recorded.
    if p_idempotency_key is not null then
        select * into v_payment
        from public.payments
        where user_id = p_user_id
          and idempotency_key = p_idempotency_key;

        if found then
            if v_payment.reservation_id <> p_reservation_id then
                raise exception 'Idempotency key was already used for another reservation'
                    using errcode = 'LM002';
            end if;
            return v_payment;
        end if;
    end if;

    if v_reservation.status <> 'PENDING_PAYMENT' then
        raise exception 'Reservation % is % and cannot be paid',
            p_reservation_id, lower(v_reservation.status)
            using errcode = 'LM002';
    end if;

    if v_reservation.expires_at <= now() then
        raise exception 'The hold on reservation % has expired', p_reservation_id
            using errcode = 'LM002';
    end if;

    insert into public.payments (
        reservation_id, user_id, amount, currency, status,
        provider_ref, failure_reason, idempotency_key
    )
    values (
        p_reservation_id, p_user_id, v_reservation.price, upper(p_currency),
        case when p_succeeded then 'SUCCEEDED' else 'FAILED' end,
        p_provider_ref,
        case when p_succeeded then null else p_failure_reason end,
        p_idempotency_key
    )
    returning * into v_payment;

    -- A failed payment leaves the reservation PENDING_PAYMENT so the customer
    -- can retry until the hold expires (FR-20).
    if p_succeeded then
        update public.reservations
        set status = 'CONFIRMED',
            expires_at = null
        where id = p_reservation_id;
    end if;

    return v_payment;
end;
$$;

-- ---------------------------------------------------------------------------
-- expire_stale_reservations: marks every lapsed unpaid reservation EXPIRED.
-- create_reservation already does this per machine; this function lets a
-- scheduled job or the machine simulator clean up everything at once.
-- ---------------------------------------------------------------------------
create or replace function public.expire_stale_reservations()
returns integer
language sql
security definer
set search_path = ''
as $$
    with expired as (
        update public.reservations
        set status = 'EXPIRED'
        where status = 'PENDING_PAYMENT'
          and expires_at <= now()
        returning 1
    )
    select count(*)::integer from expired;
$$;

-- ---------------------------------------------------------------------------
-- Availability (FR-7, FR-8). Customers cannot read other customers'
-- reservations, so these functions expose only the busy time ranges.
-- ---------------------------------------------------------------------------
create or replace function public.get_machine_busy_slots(
    p_machine_id bigint,
    p_from timestamptz,
    p_to timestamptz
)
returns table (start_time timestamptz, end_time timestamptz)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    if p_from is null or p_to is null or p_to <= p_from then
        raise exception 'End of the window must be after its start' using errcode = '22023';
    end if;

    if p_to - p_from > interval '31 days' then
        raise exception 'Availability window cannot be longer than 31 days'
            using errcode = '22023';
    end if;

    return query
        select r.start_time, r.end_time
        from public.reservations r
        where r.machine_id = p_machine_id
          and tstzrange(r.start_time, r.end_time, '[)') && tstzrange(p_from, p_to, '[)')
          and (
              r.status in ('CONFIRMED', 'IN_PROGRESS')
              or (r.status = 'PENDING_PAYMENT' and r.expires_at > now())
          )
        order by r.start_time;
end;
$$;

create or replace function public.get_available_machines(
    p_start_time timestamptz,
    p_end_time timestamptz,
    p_type text default null
)
returns setof public.machines
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    if p_start_time is null or p_end_time is null or p_end_time <= p_start_time then
        raise exception 'End time must be after start time' using errcode = '22023';
    end if;

    return query
        select m.*
        from public.machines m
        where m.active
          and m.status <> 'OUT_OF_SERVICE'
          and (p_type is null or m.type = upper(p_type))
          and not exists (
              select 1
              from public.reservations r
              where r.machine_id = m.id
                and tstzrange(r.start_time, r.end_time, '[)')
                    && tstzrange(p_start_time, p_end_time, '[)')
                and (
                    r.status in ('CONFIRMED', 'IN_PROGRESS')
                    or (r.status = 'PENDING_PAYMENT' and r.expires_at > now())
                )
          )
        order by m.id;
end;
$$;

-- ---------------------------------------------------------------------------
-- Function privileges
-- ---------------------------------------------------------------------------
revoke execute on function public.touch_row() from public, anon, authenticated;

revoke execute on function public.create_reservation(bigint, timestamptz, timestamptz, integer)
    from public, anon;
grant execute on function public.create_reservation(bigint, timestamptz, timestamptz, integer)
    to authenticated, service_role;

revoke execute on function public.cancel_reservation(bigint) from public, anon;
grant execute on function public.cancel_reservation(bigint) to authenticated, service_role;

revoke execute on function public.record_payment(uuid, bigint, boolean, text, text, text, text)
    from public, anon, authenticated;
grant execute on function public.record_payment(uuid, bigint, boolean, text, text, text, text)
    to service_role;

revoke execute on function public.expire_stale_reservations() from public, anon, authenticated;
grant execute on function public.expire_stale_reservations() to service_role;

revoke execute on function public.get_machine_busy_slots(bigint, timestamptz, timestamptz)
    from public;
grant execute on function public.get_machine_busy_slots(bigint, timestamptz, timestamptz)
    to anon, authenticated, service_role;

revoke execute on function public.get_available_machines(timestamptz, timestamptz, text)
    from public;
grant execute on function public.get_available_machines(timestamptz, timestamptz, text)
    to anon, authenticated, service_role;
