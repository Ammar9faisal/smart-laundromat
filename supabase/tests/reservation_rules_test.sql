-- Database tests for reservations, payments and access rules.
--
-- Everything runs inside one transaction that is rolled back at the end, so
-- no data is left behind. It can be run with psql against a local database,
-- or pasted into the Supabase SQL editor after the migrations are applied.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/tests/reservation_rules_test.sql
--
-- Each check prints "PASS: ..." as a notice. The first failing check raises an
-- error starting with "FAIL:" and stops the script.

begin;

-- ---------------------------------------------------------------------------
-- Fixtures: two customers, one admin, one washer, one dryer
-- ---------------------------------------------------------------------------
insert into auth.users (id, email, raw_user_meta_data) values
    ('00000000-0000-4000-8000-0000000000a1', 'test-customer-a@example.com', '{"full_name": "Test Customer A"}'),
    ('00000000-0000-4000-8000-0000000000b2', 'test-customer-b@example.com', '{"full_name": "Test Customer B"}'),
    ('00000000-0000-4000-8000-0000000000c3', 'test-admin@example.com', '{"full_name": "Test Admin"}');

-- The signup trigger normally creates these; this covers any trigger variant.
insert into public.profiles (id, full_name)
values
    ('00000000-0000-4000-8000-0000000000a1', 'Test Customer A'),
    ('00000000-0000-4000-8000-0000000000b2', 'Test Customer B'),
    ('00000000-0000-4000-8000-0000000000c3', 'Test Admin')
on conflict (id) do nothing;

update public.profiles set role = 'admin'
where id = '00000000-0000-4000-8000-0000000000c3';

with m as (
    insert into public.machines (type, capacity, price, status, active)
    values ('WASHER', 9, 5.25, 'AVAILABLE', true)
    returning id
)
select set_config('test.washer_id', id::text, true) from m;

with m as (
    insert into public.machines (type, capacity, price, status, active)
    values ('DRYER', 11, 3.75, 'OUT_OF_SERVICE', true)
    returning id
)
select set_config('test.dryer_id', id::text, true) from m;

-- All bookings happen two days from now so they are always in the future.
select set_config('test.day', (date_trunc('day', now()) + interval '2 days')::text, true);

-- ---------------------------------------------------------------------------
-- Customer A
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "00000000-0000-4000-8000-0000000000a1", "role": "authenticated"}', true);

do $$
declare
    r public.reservations;
begin
    r := public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '10 hours',
        current_setting('test.day')::timestamptz + interval '11 hours'
    );

    if r.status <> 'PENDING_PAYMENT'
       or r.price <> 5.25
       or r.user_id <> '00000000-0000-4000-8000-0000000000a1'
       or r.expires_at <> now() + interval '15 minutes' then
        raise exception 'FAIL: new reservation has unexpected values: %', r;
    end if;

    perform set_config('test.res_a', r.id::text, true);
    raise notice 'PASS: customer creates a PENDING_PAYMENT reservation priced from the machine';
end;
$$;

-- ---------------------------------------------------------------------------
-- Customer B
-- ---------------------------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "00000000-0000-4000-8000-0000000000b2", "role": "authenticated"}', true);

do $$
begin
    perform public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '10 hours 30 minutes',
        current_setting('test.day')::timestamptz + interval '11 hours 30 minutes'
    );
    raise exception 'FAIL: overlapping reservation was accepted';
exception
    when exclusion_violation then
        raise notice 'PASS: overlapping reservation rejected (23P01)';
end;
$$;

do $$
declare
    r public.reservations;
begin
    r := public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '11 hours',
        current_setting('test.day')::timestamptz + interval '12 hours'
    );
    perform set_config('test.res_b', r.id::text, true);
    raise notice 'PASS: reservation starting exactly when another ends is accepted';
end;
$$;

do $$
begin
    perform public.create_reservation(
        current_setting('test.washer_id')::bigint,
        now() - interval '2 hours',
        now() - interval '1 hour'
    );
    raise exception 'FAIL: reservation in the past was accepted';
exception
    when invalid_parameter_value then
        raise notice 'PASS: reservation in the past rejected (22023)';
end;
$$;

do $$
begin
    perform public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '15 hours',
        current_setting('test.day')::timestamptz + interval '14 hours'
    );
    raise exception 'FAIL: reservation ending before it starts was accepted';
exception
    when invalid_parameter_value then
        raise notice 'PASS: end time before start time rejected (22023)';
end;
$$;

do $$
begin
    perform public.create_reservation(
        current_setting('test.dryer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '10 hours',
        current_setting('test.day')::timestamptz + interval '11 hours'
    );
    raise exception 'FAIL: out-of-service machine was reserved';
exception
    when sqlstate 'LM001' then
        raise notice 'PASS: out-of-service machine rejected (LM001)';
end;
$$;

do $$
begin
    perform public.create_reservation(
        -1,
        current_setting('test.day')::timestamptz + interval '10 hours',
        current_setting('test.day')::timestamptz + interval '11 hours'
    );
    raise exception 'FAIL: reservation for a missing machine was accepted';
exception
    when no_data_found then
        raise notice 'PASS: missing machine rejected (P0002)';
end;
$$;

do $$
begin
    if exists (
        select 1 from public.reservations
        where id = current_setting('test.res_a')::bigint
    ) then
        raise exception 'FAIL: customer B can read customer A''s reservation';
    end if;

    if (select count(*) from public.reservations) <> 1 then
        raise exception 'FAIL: customer B should see exactly one reservation';
    end if;

    raise notice 'PASS: customers only see their own reservations';
end;
$$;

do $$
begin
    insert into public.reservations (user_id, machine_id, start_time, end_time, status, price)
    values (
        '00000000-0000-4000-8000-0000000000b2',
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '20 hours',
        current_setting('test.day')::timestamptz + interval '21 hours',
        'CONFIRMED',
        0
    );
    raise exception 'FAIL: customer inserted a reservation directly';
exception
    when insufficient_privilege then
        raise notice 'PASS: direct inserts into reservations are blocked';
end;
$$;

do $$
begin
    update public.profiles set role = 'admin'
    where id = '00000000-0000-4000-8000-0000000000b2';
    raise exception 'FAIL: customer changed their own role';
exception
    when insufficient_privilege then
        raise notice 'PASS: customers cannot change their role';
end;
$$;

do $$
declare
    v_rows integer;
begin
    update public.profiles set full_name = 'Renamed Customer B'
    where id = '00000000-0000-4000-8000-0000000000b2';
    get diagnostics v_rows = row_count;

    if v_rows <> 1 then
        raise exception 'FAIL: customer could not update their own name';
    end if;
    raise notice 'PASS: customers can update their own name';
end;
$$;

do $$
begin
    perform public.record_payment(
        '00000000-0000-4000-8000-0000000000b2',
        current_setting('test.res_b')::bigint,
        true
    );
    raise exception 'FAIL: customer called record_payment directly';
exception
    when insufficient_privilege then
        raise notice 'PASS: customers cannot record payments directly';
end;
$$;

do $$
begin
    perform public.cancel_reservation(current_setting('test.res_a')::bigint);
    raise exception 'FAIL: customer B cancelled customer A''s reservation';
exception
    when no_data_found then
        raise notice 'PASS: cancelling someone else''s reservation returns not found';
end;
$$;

do $$
begin
    if (
        select count(*)
        from public.get_machine_busy_slots(
            current_setting('test.washer_id')::bigint,
            current_setting('test.day')::timestamptz,
            current_setting('test.day')::timestamptz + interval '1 day'
        )
    ) <> 2 then
        raise exception 'FAIL: busy slots should list both reservations';
    end if;

    if exists (
        select 1
        from public.get_available_machines(
            current_setting('test.day')::timestamptz + interval '10 hours',
            current_setting('test.day')::timestamptz + interval '11 hours'
        )
        where id in (current_setting('test.washer_id')::bigint,
                     current_setting('test.dryer_id')::bigint)
    ) then
        raise exception 'FAIL: booked or out-of-service machine reported as available';
    end if;

    if not exists (
        select 1
        from public.get_available_machines(
            current_setting('test.day')::timestamptz + interval '13 hours',
            current_setting('test.day')::timestamptz + interval '14 hours',
            'washer'
        )
        where id = current_setting('test.washer_id')::bigint
    ) then
        raise exception 'FAIL: free washer not reported as available';
    end if;

    raise notice 'PASS: availability functions reflect reservations and machine status';
end;
$$;

-- ---------------------------------------------------------------------------
-- Backend (service role): payments
-- ---------------------------------------------------------------------------
reset role;
set local role service_role;

do $$
declare
    p public.payments;
    r public.reservations;
begin
    p := public.record_payment(
        '00000000-0000-4000-8000-0000000000a1',
        current_setting('test.res_a')::bigint,
        false,
        'sim_declined_1',
        'Card declined',
        'test-key-declined-1'
    );
    select * into r from public.reservations where id = current_setting('test.res_a')::bigint;

    if p.status <> 'FAILED' or p.amount <> 5.25 or r.status <> 'PENDING_PAYMENT' then
        raise exception 'FAIL: failed payment handled incorrectly: % / %', p.status, r.status;
    end if;
    raise notice 'PASS: failed payment is recorded and the reservation stays PENDING_PAYMENT';
end;
$$;

do $$
declare
    p public.payments;
    p_again public.payments;
    r public.reservations;
begin
    p := public.record_payment(
        '00000000-0000-4000-8000-0000000000a1',
        current_setting('test.res_a')::bigint,
        true,
        'sim_ok_1',
        null,
        'test-key-success-1'
    );
    select * into r from public.reservations where id = current_setting('test.res_a')::bigint;

    if p.status <> 'SUCCEEDED' or r.status <> 'CONFIRMED' or r.expires_at is not null then
        raise exception 'FAIL: successful payment did not confirm the reservation';
    end if;
    raise notice 'PASS: successful payment confirms the reservation';

    p_again := public.record_payment(
        '00000000-0000-4000-8000-0000000000a1',
        current_setting('test.res_a')::bigint,
        true,
        'sim_ok_2',
        null,
        'test-key-success-1'
    );
    if p_again.id <> p.id
       or (select count(*) from public.payments
           where reservation_id = current_setting('test.res_a')::bigint) <> 2 then
        raise exception 'FAIL: repeated idempotency key created another payment';
    end if;
    raise notice 'PASS: repeated request with the same idempotency key returns the same payment';
end;
$$;

do $$
begin
    perform public.record_payment(
        '00000000-0000-4000-8000-0000000000a1',
        current_setting('test.res_a')::bigint,
        true,
        'sim_ok_3',
        null,
        'test-key-success-2'
    );
    raise exception 'FAIL: confirmed reservation was charged twice';
exception
    when sqlstate 'LM002' then
        raise notice 'PASS: paying an already confirmed reservation is rejected (LM002)';
end;
$$;

do $$
begin
    perform public.record_payment(
        '00000000-0000-4000-8000-0000000000a1',
        current_setting('test.res_b')::bigint,
        true
    );
    raise exception 'FAIL: payment recorded against another customer''s reservation';
exception
    when no_data_found then
        raise notice 'PASS: paying for another customer''s reservation returns not found';
end;
$$;

-- ---------------------------------------------------------------------------
-- Customer A cancels; the payment is refunded and the slot is released
-- ---------------------------------------------------------------------------
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "00000000-0000-4000-8000-0000000000a1", "role": "authenticated"}', true);

do $$
declare
    r public.reservations;
begin
    r := public.cancel_reservation(current_setting('test.res_a')::bigint);

    if r.status <> 'CANCELLED' then
        raise exception 'FAIL: reservation not cancelled';
    end if;

    if not exists (
        select 1 from public.payments
        where reservation_id = r.id and status = 'REFUNDED'
    ) then
        raise exception 'FAIL: payment not refunded after early cancellation';
    end if;
    raise notice 'PASS: early cancellation cancels the reservation and refunds the payment';
end;
$$;

do $$
begin
    perform public.cancel_reservation(current_setting('test.res_a')::bigint);
    raise exception 'FAIL: cancelled reservation was cancelled again';
exception
    when sqlstate 'LM002' then
        raise notice 'PASS: cancelled reservation cannot be cancelled again (LM002)';
end;
$$;

do $$
begin
    perform public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '10 hours',
        current_setting('test.day')::timestamptz + interval '11 hours'
    );
    raise notice 'PASS: a cancelled slot can be booked again';
end;
$$;

-- ---------------------------------------------------------------------------
-- Unpaid reservations stop blocking the slot once their hold expires (FR-16)
-- ---------------------------------------------------------------------------
reset role;
update public.reservations
set expires_at = now() - interval '1 minute'
where id = current_setting('test.res_b')::bigint;

set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "00000000-0000-4000-8000-0000000000a1", "role": "authenticated"}', true);

do $$
begin
    perform public.create_reservation(
        current_setting('test.washer_id')::bigint,
        current_setting('test.day')::timestamptz + interval '11 hours',
        current_setting('test.day')::timestamptz + interval '12 hours'
    );
    raise notice 'PASS: an expired unpaid hold no longer blocks the slot';
end;
$$;

reset role;

do $$
begin
    if (select status from public.reservations
        where id = current_setting('test.res_b')::bigint) <> 'EXPIRED' then
        raise exception 'FAIL: lapsed reservation was not marked EXPIRED';
    end if;
    raise notice 'PASS: lapsed reservation is marked EXPIRED';
end;
$$;

-- ---------------------------------------------------------------------------
-- Admin and anonymous access
-- ---------------------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims', '{"sub": "00000000-0000-4000-8000-0000000000c3", "role": "authenticated"}', true);

do $$
begin
    if (
        select count(*) from public.reservations
        where machine_id = current_setting('test.washer_id')::bigint
    ) < 4 then
        raise exception 'FAIL: admin cannot see all reservations';
    end if;

    if not exists (
        select 1 from public.payments
        where user_id = '00000000-0000-4000-8000-0000000000a1'
    ) then
        raise exception 'FAIL: admin cannot see customer payments';
    end if;
    raise notice 'PASS: admins can view all reservations and payments';
end;
$$;

reset role;
set local role anon;

do $$
begin
    perform count(*) from public.reservations;
    raise exception 'FAIL: anonymous user read reservations';
exception
    when insufficient_privilege then
        raise notice 'PASS: anonymous users cannot read reservations';
end;
$$;

reset role;

rollback;
