"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppNav from "@/components/AppNav";
import { ApiError, api, errorText, getAccessToken } from "@/lib/api";
import {
  formatDateTime,
  formatMoney,
  statusClass,
  titleCase,
} from "@/lib/format";
import {
  TEST_PAYMENT_METHODS,
  type Payment,
  type Reservation,
} from "@/lib/types";

export default function ReservationsPage() {
  const router = useRouter();

  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [method, setMethod] = useState<string>(TEST_PAYMENT_METHODS[0].value);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [mine, myPayments] = await Promise.all([
        api<Reservation[]>("/api/reservations?mine=true"),
        api<Payment[]>("/api/payments?mine=true"),
      ]);
      setReservations(mine);
      setPayments(myPayments);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      setError(errorText(err, "Unable to load reservations"));
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    getAccessToken().then((token) => {
      if (!token) {
        router.replace("/login");
        return;
      }
      if (new URLSearchParams(window.location.search).get("created")) {
        setMessage(
          "Reservation created. Pay within 15 minutes to confirm it."
        );
      }
      load();
    });
  }, [load, router]);

  async function pay(reservation: Reservation) {
    setBusyId(reservation.id);
    setError("");
    setMessage("");

    try {
      await api<Payment>("/api/payments", {
        method: "POST",
        body: {
          reservation_id: reservation.id,
          payment_method: method,
          idempotency_key: crypto.randomUUID(),
        },
      });
      setMessage(`Payment received. Reservation #${reservation.id} is confirmed.`);
    } catch (err) {
      setError(errorText(err, "Payment failed"));
    } finally {
      setBusyId(null);
      load();
    }
  }

  async function cancel(reservation: Reservation) {
    if (!window.confirm(`Cancel reservation #${reservation.id}?`)) return;

    setBusyId(reservation.id);
    setError("");
    setMessage("");

    try {
      await api<Reservation>(`/api/reservations/${reservation.id}`, {
        method: "DELETE",
      });
      setMessage(
        reservation.status === "CONFIRMED"
          ? `Reservation #${reservation.id} cancelled. Payments made more than 15 minutes before the start are refunded.`
          : `Reservation #${reservation.id} cancelled.`
      );
    } catch (err) {
      setError(errorText(err, "Unable to cancel reservation"));
    } finally {
      setBusyId(null);
      load();
    }
  }

  function paymentsFor(reservationId: number) {
    return payments.filter((p) => p.reservation_id === reservationId);
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <AppNav />

      <main className="mx-auto max-w-5xl space-y-6 p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-3xl font-bold">My Reservations</h1>

          <label className="flex items-center gap-2 text-sm">
            Pay with
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="rounded border p-2"
            >
              {TEST_PAYMENT_METHODS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="text-sm text-gray-600">
          Payments are simulated with test cards. No real card details are
          collected.
        </p>

        {message && (
          <p className="rounded bg-green-50 p-3 text-green-800">{message}</p>
        )}
        {error && <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>}

        {loading ? (
          <p>Loading reservations...</p>
        ) : reservations.length === 0 ? (
          <p className="text-gray-600">
            You have no reservations yet.{" "}
            <Link href="/machines" className="text-blue-600">
              Browse machines
            </Link>
          </p>
        ) : (
          <div className="space-y-4">
            {reservations.map((reservation) => (
              <div
                key={reservation.id}
                className="rounded-xl border bg-white p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold">
                    #{reservation.id} ·{" "}
                    {reservation.machine
                      ? `${titleCase(reservation.machine.type)} #${reservation.machine.id}`
                      : `Machine #${reservation.machine_id}`}
                  </h2>
                  <span className={statusClass(reservation.status)}>
                    {titleCase(reservation.status)}
                  </span>
                </div>

                <p className="mt-1 text-gray-700">
                  {formatDateTime(reservation.start_time)} –{" "}
                  {formatDateTime(reservation.end_time)} ·{" "}
                  {formatMoney(reservation.price)}
                </p>

                {reservation.status === "PENDING_PAYMENT" && (
                  <p className="mt-1 text-sm text-yellow-800">
                    Pay before {formatDateTime(reservation.expires_at)} or
                    the slot is released.
                  </p>
                )}

                {paymentsFor(reservation.id).length > 0 && (
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {paymentsFor(reservation.id).map((payment) => (
                      <li key={payment.id}>
                        Payment #{payment.id}:{" "}
                        <span className={statusClass(payment.status)}>
                          {titleCase(payment.status)}
                        </span>{" "}
                        {formatMoney(payment.amount, payment.currency)}
                        {payment.failure_reason &&
                          ` — ${payment.failure_reason}`}
                      </li>
                    ))}
                  </ul>
                )}

                {["PENDING_PAYMENT", "CONFIRMED"].includes(
                  reservation.status
                ) && (
                  <div className="mt-4 flex gap-3">
                    {reservation.status === "PENDING_PAYMENT" && (
                      <button
                        onClick={() => pay(reservation)}
                        disabled={busyId === reservation.id}
                        className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50"
                      >
                        {busyId === reservation.id ? "Working..." : "Pay now"}
                      </button>
                    )}
                    <button
                      onClick={() => cancel(reservation)}
                      disabled={busyId === reservation.id}
                      className="rounded border border-red-600 px-4 py-2 text-red-600 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
