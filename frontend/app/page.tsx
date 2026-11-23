
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      {/* Navigation */}
      <nav className="flex items-center justify-between border-b bg-white px-8 py-5">
        <Link href="/" className="text-xl font-bold text-blue-600">
          Smart Laundromat
        </Link>

        <div className="flex gap-5">
          <Link href="/machines" className="hover:text-blue-600">
            Machines
          </Link>

          <Link href="/login" className="hover:text-blue-600">
            Login
          </Link>

          <Link href="/signup" className="hover:text-blue-600">
            Sign Up
          </Link>

          <Link href="/dashboard" className="hover:text-blue-600">
            Dashboard
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="mb-6 text-5xl font-bold">
          Welcome to Smart Laundromat
        </h1>

        <p className="mb-8 text-lg text-gray-600">
          Find available washers and dryers, reserve your
          preferred time slot, and manage your laundry
          appointments all in one place.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/signup"
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Get Started
          </Link>

          <Link
            href="/login"
            className="rounded-lg border border-blue-600 px-6 py-3 font-semibold text-blue-600 hover:bg-blue-50"
          >
            Login
          </Link>

          <Link
            href="/machines"
            className="rounded-lg border border-blue-600 px-6 py-3 font-semibold text-blue-600 hover:bg-blue-50"
          >
            Browse Machines
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto grid max-w-5xl gap-6 px-6 pb-20 md:grid-cols-3">
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-xl font-semibold">
            Browse Machines
          </h2>
          <p className="text-gray-600">
            Check available washers and dryers before
            visiting the laundromat.
          </p>
        </div>

        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-xl font-semibold">
            Book Reservations
          </h2>
          <p className="text-gray-600">
            Reserve a machine for your preferred time slot
            and pay with a simulated card.
          </p>
        </div>

        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-xl font-semibold">
            Manage Your Account
          </h2>
          <p className="text-gray-600">
            View your profile and manage your laundry
            reservations from one dashboard.
          </p>
        </div>
      </section>

      {/* Developer Links */}
      <section className="border-t bg-white px-6 py-10 text-center">
        <h2 className="mb-4 text-xl font-semibold">
          Development & Testing
        </h2>

        <p className="mb-5 text-gray-600">
          Quick links for team members testing the application.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-gray-800 px-5 py-3 text-white hover:bg-gray-700"
          >
            FastAPI Docs
          </a>

          <a
            href="http://127.0.0.1:8000/api/machines/"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-gray-800 px-5 py-3 text-white hover:bg-gray-700"
          >
            Test Machines API
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-gray-50 py-6 text-center text-sm text-gray-500">
        EECS 4413 — Smart Laundromat Service Platform
      </footer>
    </main>
  );
}
