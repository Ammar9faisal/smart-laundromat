
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

type Profile = {
  id: string;
  email: string;
  full_name: string | null;
  role: "customer" | "admin";
  created_at: string;
};

export default function DashboardPage() {
  const router = useRouter();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        const { data, error: authError } =
          await supabase.auth.getUser();

        if (authError || !data.user) {
          router.replace("/login");
          return;
        }

        const { data: sessionData } =
          await supabase.auth.getSession();

        const token = sessionData.session?.access_token;

        if (!token) {
          router.replace("/login");
          return;
        }

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(
            `Failed to load profile (${response.status})`
          );
        }

        const result: Profile = await response.json();

        if (active) {
          setProfile(result);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load profile"
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProfile();

    return () => {
      active = false;
    };
  }, [router]);

  async function handleLogout() {
    const { error } = await supabase.auth.signOut();

    if (error) {
      setError(error.message);
      return;
    }

    router.replace("/login");
  }

  if (loading) {
    return <main className="p-8">Loading dashboard...</main>;
  }

  if (error) {
    return <main className="p-8 text-red-600">{error}</main>;
  }

  if (!profile) return null;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="mb-6 text-3xl font-bold">
        Smart Laundromat Dashboard
      </h1>

      <div className="space-y-3 rounded border p-6">
        <h2 className="text-xl font-semibold">
          Welcome, {profile.full_name || profile.email}!
        </h2>

        <p>Email: {profile.email}</p>
        <p>Role: {profile.role}</p>

        {profile.role === "admin" && (
          <p className="font-semibold text-blue-600">
            Administrator Account
          </p>
        )}
      </div>

      <button
        onClick={handleLogout}
        className="mt-6 rounded bg-red-600 px-5 py-3 text-white"
      >
        Log Out
      </button>
    </main>
  );
}
