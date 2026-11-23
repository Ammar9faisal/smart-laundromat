
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Machine = {
  id: number;
  type: string;
  capacity: number;
  price: number;
  status: string;
  active: boolean;
};

export default function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadMachines() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/machines/`
        );

        if (!response.ok) {
          throw new Error("Failed to load machines");
        }

        const data: Machine[] = await response.json();
        setMachines(data);
      } catch {
        setError("Could not connect to the backend.");
      } finally {
        setLoading(false);
      }
    }

    loadMachines();
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10 text-gray-900">
      <div className="mx-auto max-w-6xl">
        <Link href="/" className="text-blue-600 hover:underline">
          ← Back to Home
        </Link>

        <h1 className="mt-6 text-3xl font-bold">
          Laundry Machines
        </h1>

        <p className="mt-2 text-gray-600">
          Browse our available washers and dryers.
        </p>

        {loading && (
          <p className="mt-8">Loading machines...</p>
        )}

        {error && (
          <p className="mt-8 text-red-600">{error}</p>
        )}

        {!loading && !error && machines.length === 0 && (
          <p className="mt-8">No machines found.</p>
        )}

        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {machines.map((machine) => (
            <div
              key={machine.id}
              className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-bold">
                  {machine.type === "WASHER"
                    ? "Washer"
                    : machine.type === "DRYER"
                      ? "Dryer"
                      : machine.type}{" "}
                  #{machine.id}
                </h2>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    machine.status === "AVAILABLE"
                      ? "bg-green-100 text-green-700"
                      : "bg-orange-100 text-orange-700"
                  }`}
                >
                  {machine.status}
                </span>
              </div>

              <p className="mb-2 text-gray-600">
                Capacity: {machine.capacity} kg
              </p>

              <p className="mb-6 text-2xl font-bold">
                ${Number(machine.price).toFixed(2)}
              </p>

              <button
                disabled
                className="w-full cursor-not-allowed rounded-lg bg-gray-200 px-4 py-3 text-gray-500"
              >
                Booking Coming Soon
              </button>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
