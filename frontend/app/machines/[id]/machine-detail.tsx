"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import AppNav from "@/components/AppNav";
import { api, errorText, getAccessToken } from "@/lib/api";
import {
  formatMoney,
  formatTime,
  localDateTime,
  nextHourDefaults,
  statusClass,
  titleCase,
} from "@/lib/format";
import type { Machine, MachineAvailability } from "@/lib/types";
import { useIsClient } from "@/lib/use-is-client";

const DURATIONS = [30, 45, 60, 90, 120];

export default function MachineDetail() {
  const { id } = useParams<{ id: string }>();
  const isClient = useIsClient();

  // The booking form's defaults depend on the user's clock and the URL, so
  // the page body is only rendered in the browser.
  if (!isClient) {
    return <main className="p-8">Loading machine...</main>;
  }

  return <MachineDetailView id={id} />;
}

/** Defaults from the "Find a free machine" search link, else the next hour. */
function bookingDefaults() {
  const query = new URLSearchParams(window.location.search);
  const fallback = nextHourDefaults();
  return {
    date: query.get("date") ?? fallback.date,
    time: query.get("start") ?? fallback.time,
    duration: Number(query.get("duration")) || 60,
  };
}

function MachineDetailView({ id }: { id: string }) {
  const router = useRouter();

  const [defaults] = useState(bookingDefaults);
  const [machine, setMachine] = useState<Machine | null>(null);
  const [availability, setAvailability] =
    useState<MachineAvailability | null>(null);
  const [signedIn, setSignedIn] = useState(false);

  const [date, setDate] = useState(defaults.date);
  const [startTime, setStartTime] = useState(defaults.time);
  const [duration, setDuration] = useState(defaults.duration);

  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState("");
  const [availabilityError, setAvailabilityError] = useState("");

  useEffect(() => {
    getAccessToken().then((token) => setSignedIn(Boolean(token)));
  }, []);

  useEffect(() => {
    api<Machine>(`/api/machines/${id}`)
      .then(setMachine)
      .catch((err) => setError(errorText(err, "Unable to load machine")))
      .finally(() => setLoading(false));
  }, [id]);

  // Bumped after a failed booking so the busy slots are fetched again.
  const [availabilityVersion, setAvailabilityVersion] = useState(0);

  useEffect(() => {
    if (!date) return;
    let ignore = false;

    async function loadAvailability() {
      const from = localDateTime(date, "00:00");
      const to = new Date(from.getTime() + 24 * 60 * 60_000);
      const params = new URLSearchParams({
        from: from.toISOString(),
        to: to.toISOString(),
      });

      try {
        const data = await api<MachineAvailability>(
          `/api/machines/${id}/availability?${params}`
        );
        if (ignore) return;
        setAvailability(data);
        setAvailabilityError("");
      } catch (err) {
        if (!ignore) {
          setAvailabilityError(errorText(err, "Unable to load availability"));
        }
      }
    }

    loadAvailability();

    return () => {
      ignore = true;
    };
  }, [id, date, availabilityVersion]);

  async function handleReserve(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBooking(true);
    setError("");

    const start = localDateTime(date, startTime);
    const end = new Date(start.getTime() + duration * 60_000);

    try {
      await api("/api/reservations", {
        method: "POST",
        body: {
          machine_id: Number(id),
          start_time: start.toISOString(),
          end_time: end.toISOString(),
        },
      });
      router.push("/reservations?created=1");
    } catch (err) {
      setError(errorText(err, "Unable to create reservation"));
      setAvailabilityVersion((v) => v + 1);
    } finally {
      setBooking(false);
    }
  }

  if (loading) {
    return <main className="p-8">Loading machine...</main>;
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <AppNav />

      <main className="mx-auto max-w-3xl space-y-6 p-8">
        <Link href="/machines" className="text-blue-600">
          ← All machines
        </Link>

        {!machine ? (
          <p className="text-red-600">{error || "Machine not found"}</p>
        ) : (
          <>
            <section className="rounded-xl border bg-white p-6">
              <div className="mb-2 flex items-center justify-between">
                <h1 className="text-3xl font-bold">
                  {titleCase(machine.type)} #{machine.id}
                </h1>
                <span className={statusClass(machine.status)}>
                  {titleCase(machine.status)}
                </span>
              </div>
              <p className="text-gray-600">
                {machine.capacity} kg · {formatMoney(machine.price)} per
                reservation
              </p>
            </section>

            <section className="rounded-xl border bg-white p-6">
              <h2 className="mb-4 text-xl font-semibold">Reserve</h2>

              {machine.status === "OUT_OF_SERVICE" ? (
                <p className="text-red-600">
                  This machine is out of service and cannot be reserved.
                </p>
              ) : !signedIn ? (
                <p>
                  <Link href="/login" className="text-blue-600">
                    Log in
                  </Link>{" "}
                  to reserve this machine.
                </p>
              ) : (
                <form
                  onSubmit={handleReserve}
                  className="flex flex-wrap items-end gap-4"
                >
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
                    disabled={booking}
                    className="rounded bg-blue-600 px-5 py-2 text-white disabled:opacity-50"
                  >
                    {booking ? "Reserving..." : "Reserve"}
                  </button>
                </form>
              )}

              {error && <p className="mt-4 text-red-600">{error}</p>}

              <p className="mt-4 text-sm text-gray-600">
                You will have 15 minutes to pay before the slot is
                released.
              </p>
            </section>

            <section className="rounded-xl border bg-white p-6">
              <h2 className="mb-4 text-xl font-semibold">
                Booked times on {date}
              </h2>

              {availabilityError ? (
                <p className="text-red-600">{availabilityError}</p>
              ) : !availability ? (
                <p>Loading availability...</p>
              ) : availability.busy.length === 0 ? (
                <p className="text-green-700">
                  No bookings yet — the whole day is free.
                </p>
              ) : (
                <ul className="space-y-1">
                  {availability.busy.map((slot) => (
                    <li key={slot.start_time} className="text-gray-700">
                      {formatTime(slot.start_time)} –{" "}
                      {formatTime(slot.end_time)}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
