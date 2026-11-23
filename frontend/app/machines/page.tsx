"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppNav from "@/components/AppNav";
import { api, errorText } from "@/lib/api";
import {
  formatMoney,
  localDateTime,
  nextHourDefaults,
  statusClass,
  titleCase,
} from "@/lib/format";
import type { Machine, MachineType } from "@/lib/types";
import { useIsClient } from "@/lib/use-is-client";

const DURATIONS = [30, 45, 60, 90, 120];

export default function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [type, setType] = useState<"" | MachineType>("");
  const [minCapacity, setMinCapacity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;

    async function loadMachines() {
      const params = new URLSearchParams();
      if (type) params.set("type", type);
      if (minCapacity) params.set("min_capacity", minCapacity);

      try {
        const data = await api<Machine[]>(`/api/machines/?${params}`);
        if (ignore) return;
        setMachines(data);
        setError("");
      } catch (err) {
        if (!ignore) setError(errorText(err, "Unable to load machines"));
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    loadMachines();

    return () => {
      ignore = true;
    };
  }, [type, minCapacity]);

  const isClient = useIsClient();

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <AppNav />

      <main className="mx-auto max-w-5xl space-y-8 p-8">
        <h1 className="text-3xl font-bold">Machines</h1>

        {/* Filters */}
        <section className="flex flex-wrap items-end gap-4 rounded-xl border bg-white p-6">
          <label className="flex flex-col text-sm">
            Type
            <select
              value={type}
              onChange={(e) => setType(e.target.value as "" | MachineType)}
              className="mt-1 rounded border p-2"
            >
              <option value="">All</option>
              <option value="WASHER">Washers</option>
              <option value="DRYER">Dryers</option>
            </select>
          </label>

          <label className="flex flex-col text-sm">
            Minimum capacity (kg)
            <input
              type="number"
              min={1}
              value={minCapacity}
              onChange={(e) => setMinCapacity(e.target.value)}
              className="mt-1 w-40 rounded border p-2"
            />
          </label>
        </section>

        {/* Find a free machine for a time slot */}
        {isClient && <FindFreeMachine type={type} />}

        {error && <p className="text-red-600">{error}</p>}

        {/* All machines */}
        <section>
          {loading ? (
            <p>Loading machines...</p>
          ) : machines.length === 0 ? (
            <p className="text-gray-600">No machines match these filters.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {machines.map((machine) => (
                <Link
                  key={machine.id}
                  href={`/machines/${machine.id}`}
                  className="rounded-xl border bg-white p-5 shadow-sm hover:border-blue-400"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-lg font-semibold">
                      {titleCase(machine.type)} #{machine.id}
                    </h3>
                    <span className={statusClass(machine.status)}>
                      {titleCase(machine.status)}
                    </span>
                  </div>
                  <p className="text-gray-600">
                    {machine.capacity} kg · {formatMoney(machine.price)}{" "}
                    per cycle
                  </p>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

/** Rendered only in the browser, so the default date and time come from the
 * user's clock and time zone. */
function FindFreeMachine({ type }: { type: "" | MachineType }) {
  const [date, setDate] = useState(() => nextHourDefaults().date);
  const [startTime, setStartTime] = useState(() => nextHourDefaults().time);
  const [duration, setDuration] = useState(60);
  const [available, setAvailable] = useState<Machine[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  async function findAvailable(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSearching(true);
    setError("");

    const start = localDateTime(date, startTime);
    const end = new Date(start.getTime() + duration * 60_000);
    const params = new URLSearchParams({
      start_time: start.toISOString(),
      end_time: end.toISOString(),
    });
    if (type) params.set("type", type);

    try {
      setAvailable(await api<Machine[]>(`/api/machines/available?${params}`));
    } catch (err) {
      setError(errorText(err, "Unable to search availability"));
    } finally {
      setSearching(false);
    }
  }

  function bookingLink(machineId: number) {
    const params = new URLSearchParams({
      date,
      start: startTime,
      duration: String(duration),
    });
    return `/machines/${machineId}?${params}`;
  }

  return (
    <section className="rounded-xl border bg-white p-6">
      <h2 className="mb-4 text-xl font-semibold">Find a free machine</h2>

      <form onSubmit={findAvailable} className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col text-sm">
          Date
          <input
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="mt-1 rounded border p-2"
          />
        </label>

        <label className="flex flex-col text-sm">
          Start time
          <input
            type="time"
            required
            step={900}
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className="mt-1 rounded border p-2"
          />
        </label>

        <label className="flex flex-col text-sm">
          Duration
          <select
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="mt-1 rounded border p-2"
          >
            {DURATIONS.map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes} minutes
              </option>
            ))}
          </select>
        </label>

        <button
          type="submit"
          disabled={searching || !date || !startTime}
          className="rounded bg-blue-600 px-5 py-2 text-white disabled:opacity-50"
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {available && (
        <div className="mt-4">
          {available.length === 0 ? (
            <p className="text-gray-600">
              No machines are free for that time. Try another slot.
            </p>
          ) : (
            <ul className="divide-y">
              {available.map((machine) => (
                <li
                  key={machine.id}
                  className="flex items-center justify-between py-2"
                >
                  <span>
                    {titleCase(machine.type)} #{machine.id} ·{" "}
                    {machine.capacity} kg · {formatMoney(machine.price)}
                  </span>
                  <Link
                    href={bookingLink(machine.id)}
                    className="rounded bg-green-600 px-4 py-1 text-white"
                  >
                    Book
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
