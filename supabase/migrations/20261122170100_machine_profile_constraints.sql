-- Constraints and access rules for machines and profiles
--
-- * CHECK constraints for the values the API and design document rely on
--   (FR-6, FR-9 machine types and states; FR-5 roles).
-- * Customers can only change their own name, never their role
--   ("users must never be able to promote themselves to admin").
-- * is_admin() helper used by row level security policies in this and later
--   migrations.
--
-- The current rows in the shared project already satisfy every constraint.

-- ---------------------------------------------------------------------------
-- CHECK constraints (added only if a constraint with the same name is missing)
-- ---------------------------------------------------------------------------
do $constraints$
begin
    if not exists (select 1 from pg_constraint where conname = 'machines_type_check') then
        alter table public.machines
            add constraint machines_type_check check (type in ('WASHER', 'DRYER'));
    end if;

    if not exists (select 1 from pg_constraint where conname = 'machines_status_check') then
        alter table public.machines
            add constraint machines_status_check
            check (status in ('AVAILABLE', 'RESERVED', 'IN_USE', 'OUT_OF_SERVICE'));
    end if;

    if not exists (select 1 from pg_constraint where conname = 'machines_capacity_check') then
        alter table public.machines
            add constraint machines_capacity_check check (capacity > 0);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'machines_price_check') then
        alter table public.machines
            add constraint machines_price_check check (price >= 0);
    end if;

    if not exists (select 1 from pg_constraint where conname = 'profiles_role_check') then
        alter table public.profiles
            add constraint profiles_role_check check (role in ('customer', 'admin'));
    end if;
end;
$constraints$;

create index if not exists machines_type_status_idx
    on public.machines (type, status)
    where active;

-- ---------------------------------------------------------------------------
-- Role helper
-- ---------------------------------------------------------------------------
-- SECURITY DEFINER so policies can read profiles.role without being blocked by
-- the profiles policies themselves.
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.profiles
        where id = (select auth.uid())
          and role = 'admin'
    );
$$;

revoke execute on function public.is_admin() from public, anon;
grant execute on function public.is_admin() to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Profiles: customers may edit their name only
-- ---------------------------------------------------------------------------
-- Column-level privileges are checked before RLS, so even a permissive update
-- policy cannot be used to change "role" or "id".
revoke insert, update, delete on public.profiles from anon, authenticated;
grant update (full_name) on public.profiles to authenticated;

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
    on public.profiles
    for update
    to authenticated
    using (id = (select auth.uid()))
    with check (id = (select auth.uid()));

drop policy if exists "Admins can view all profiles" on public.profiles;
create policy "Admins can view all profiles"
    on public.profiles
    for select
    to authenticated
    using ((select public.is_admin()));

-- ---------------------------------------------------------------------------
-- Machines: administrators manage machines (FR-33). Machines are deactivated
-- with active = false instead of being deleted, so there is no delete policy.
-- ---------------------------------------------------------------------------
drop policy if exists "Admins can view all machines" on public.machines;
create policy "Admins can view all machines"
    on public.machines
    for select
    to authenticated
    using ((select public.is_admin()));

drop policy if exists "Admins can add machines" on public.machines;
create policy "Admins can add machines"
    on public.machines
    for insert
    to authenticated
    with check ((select public.is_admin()));

drop policy if exists "Admins can update machines" on public.machines;
create policy "Admins can update machines"
    on public.machines
    for update
    to authenticated
    using ((select public.is_admin()))
    with check ((select public.is_admin()));

revoke insert, update, delete on public.machines from anon;
revoke delete on public.machines from authenticated;
