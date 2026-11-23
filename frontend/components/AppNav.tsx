"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Profile } from "@/lib/types";

export default function AppNav() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(async ({ data }) => {
      if (!data.session) return;
      try {
        const me = await api<Profile>("/api/auth/me");
        if (active) setProfile(me);
      } catch {
        // Navigation still works without the profile.
      }
    });

    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    await supabase.auth.signOut();
    setProfile(null);
    router.replace("/login");
  }

  return (
    <nav className="flex flex-wrap items-center justify-between gap-4 border-b bg-white px-8 py-5 text-gray-900">
      <Link href="/" className="text-xl font-bold text-blue-600">
        Smart Laundromat
      </Link>

      <div className="flex flex-wrap items-center gap-5">
        <Link href="/machines" className="hover:text-blue-600">
          Machines
        </Link>

        {profile ? (
          <>
            <Link href="/reservations" className="hover:text-blue-600">
              My Reservations
            </Link>
            {profile.role === "admin" && (
              <Link href="/admin" className="hover:text-blue-600">
                Admin
              </Link>
            )}
            <Link href="/dashboard" className="hover:text-blue-600">
              Dashboard
            </Link>
            <button
              onClick={handleLogout}
              className="text-red-600 hover:underline"
            >
              Log Out
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="hover:text-blue-600">
              Login
            </Link>
            <Link href="/signup" className="hover:text-blue-600">
              Sign Up
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
