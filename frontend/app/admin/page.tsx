"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppNav from "@/components/AppNav";
import { ApiError, api, errorText } from "@/lib/api";
import {
  formatDateTime,
  formatMoney,
  statusClass,
  titleCase,
} from "@/lib/format";
import type {
  AdminSummary,
  Machine,
  MachineStatus,
  MachineType,
  Payment,
  Profile,
  Reservation,
} from "@/lib/types";

const STATUSES: MachineStatus[] = [
  "AVAILABLE",
  "RESERVED",
  "IN_USE",
  "OUT_OF_SERVICE",
];

export default function AdminPage() {
  const router = useRouter();

  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [error, setError] = useState("");

  const [newType, setNewType] = useState<MachineType>("WASHER");
  const [newCapacity, setNewCapacity] = useState("8");
  const [newPrice, setNewPrice] = useState("4.50");

  const load = useCallback(async () => {
    try {
      const [s, m, r, p] = await Promise.all([
        api<AdminSummary>("/api/admin/summary"),
        api<Machine[]>("/api/admin/machines"),
        api<Reservation[]>("/api/reservations?limit=200"),
        api<Payment[]>("/api/payments?limit=200"),
      ]);
      setSummary(s);
      setMachines(m);
      setReservations(r);
      setPayments(p);
    } catch (err) {
      setError(errorText(err, "Unable to load admin data"));
    }
  }, []);

  // The backend enforces the admin role on every admin endpoint; this check
  // only decides what to show.
  useEffect(() => {
    api<Profile>("/api/auth/me")
      .then((me) => {
        setAllowed(me.role === "admin");
        if (me.role === "admin") load();
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setAllowed(false);
      });
  }, [load, router]);

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
    } catch (err) {
      setError(errorText(err, "Action failed"));
    }
    load();
  }

  function changeStatus(machine: Machine, status: MachineStatus) {
    run(() =>
      api(`/api/machines/${machine.id}/status`, {
        method: "PATCH",
        body: { status },
      })
    );
  }

  function toggleActive(machine: Machine) {
    run(() =>
      machine.active
        ? api(`/api/machines/${machine.id}`, { method: "DELETE" })
        : api(`/api/machines/${machine.id}`, {
            method: "PATCH",
            body: { active: true },
          })
    );
  }

  function addMachine(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    run(() =>
      api("/api/machines/", {
        method: "POST",
        body: {
          type: newType,
          capacity: Number(newCapacity),
          price: newPrice,
        },
      })
    );
  }

  if (allowed === null) {
    return <main className="p-8">Loading...</main>;
  }

  if (!allowed) {
    return (
      <div className="min-h-screen bg-gray-50 text-gray-900">
        <AppNav />
        <main className="p-8 text-red-600">
          Administrator access required.
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <AppNav />

      <main className="mx-auto max-w-6xl space-y-8 p-8">
        <h1 className="text-3xl font-bold">Administration</h1>

        {error && <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>}

        {/* Summary (FR-35) */}
        {summary && (
          <section className="grid gap-4 md:grid-cols-4">
            <Stat
              label="Machines"
              value={`${summary.machines.active} active / ${summary.machines.total}`}
            />
            <Stat
              label="Out of service"
              value={String(summary.machines.out_of_service)}
            />
            <Stat
              label="Confirmed reservations"
              value={String(summary.reservations_by_status.CONFIRMED ?? 0)}
            />
            <Stat
              label="Revenue"
              value={`${formatMoney(summary.payments.revenue)} (${summary.payments.succeeded} payments)`}
            />
          </section>
        )}

        {/* Machines (FR-10, FR-33) */}
        <section className="rounded-xl border bg-white p-6">
          <h2 className="mb-4 text-xl font-semibold">Machines</h2>

          <form
            onSubmit={addMachine}
            className="mb-6 flex flex-wrap items-end gap-3"
          >
            <label className="flex flex-col text-sm">
              Type
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as MachineType)}
                className="mt-1 rounded border p-2"
              >
                <option value="WASHER">Washer</option>
                <option value="DRYER">Dryer</option>
              </select>
            </label>
            <label className="flex flex-col text-sm">
              Capacity (kg)
              <input
                type="number"
                min={1}
                max={100}
                required
                value={newCapacity}
                onChange={(e) => setNewCapacity(e.target.value)}
                className="mt-1 w-28 rounded border p-2"
              />
            </label>
            <label className="flex flex-col text-sm">
              Price (CAD)
              <input
                type="number"
                min={0}
                step="0.01"
                required
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="mt-1 w-28 rounded border p-2"
              />
            </label>
            <button
              type="submit"
              className="rounded bg-blue-600 px-4 py-2 text-white"
            >
              Add machine
            </button>
          </form>

          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-gray-600">
                <th className="py-2">Machine</th>
                <th>Capacity</th>
                <th>Price</th>
                <th>Status</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {machines.map((machine) => (
                <tr key={machine.id} className="border-b">
                  <td className="py-2">
                    {titleCase(machine.type)} #{machine.id}
                  </td>
                  <td>{machine.capacity} kg</td>
                  <td>{formatMoney(machine.price)}</td>
                  <td>
                    <select
                      value={machine.status}
                      onChange={(e) =>
                        changeStatus(machine, e.target.value as MachineStatus)
                      }
                      className="rounded border p-1"
                    >
                      {STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {titleCase(status)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button
                      onClick={() => toggleActive(machine)}
                      className={
                        machine.active
                          ? "text-red-600 hover:underline"
                          : "text-green-700 hover:underline"
                      }
                    >
                      {machine.active ? "Deactivate" : "Reactivate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Reservations (FR-34) */}
        <section className="rounded-xl border bg-white p-6">
          <h2 className="mb-4 text-xl font-semibold">Reservations</h2>
          {reservations.length === 0 ? (
            <p className="text-gray-600">No reservations yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-gray-600">
                  <th className="py-2">#</th>
                  <th>Machine</th>
                  <th>Time</th>
                  <th>Customer</th>
                  <th>Price</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((r) => (
                  <tr key={r.id} className="border-b">
                    <td className="py-2">{r.id}</td>
                    <td>#{r.machine_id}</td>
                    <td>
                      {formatDateTime(r.start_time)} –{" "}
                      {formatDateTime(r.end_time)}
                    </td>
                    <td className="font-mono text-xs">
                      {r.user_id.slice(0, 8)}
                    </td>
                    <td>{formatMoney(r.price)}</td>
                    <td>
                      <span className={statusClass(r.status)}>
                        {titleCase(r.status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* Payments (UC8: inspect basic payment information) */}
        <section className="rounded-xl border bg-white p-6">
          <h2 className="mb-4 text-xl font-semibold">Payments</h2>
          {payments.length === 0 ? (
            <p className="text-gray-600">No payments yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-gray-600">
                  <th className="py-2">#</th>
                  <th>Reservation</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Reference</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id} className="border-b">
                    <td className="py-2">{p.id}</td>
                    <td>#{p.reservation_id}</td>
                    <td>{formatMoney(p.amount, p.currency)}</td>
                    <td>
                      <span className={statusClass(p.status)}>
                        {titleCase(p.status)}
                      </span>
                      {p.failure_reason && (
                        <span className="ml-2 text-gray-500">
                          {p.failure_reason}
                        </span>
                      )}
                    </td>
                    <td className="font-mono text-xs">{p.provider_ref}</td>
                    <td>{formatDateTime(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <p className="text-sm text-gray-600">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
