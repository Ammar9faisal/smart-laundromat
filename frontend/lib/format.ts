export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatMoney(amount: number, currency = "CAD"): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(amount);
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const STATUS_COLOURS: Record<string, string> = {
  AVAILABLE: "bg-green-100 text-green-800",
  CONFIRMED: "bg-green-100 text-green-800",
  SUCCEEDED: "bg-green-100 text-green-800",
  COMPLETED: "bg-gray-100 text-gray-700",
  RESERVED: "bg-yellow-100 text-yellow-800",
  PENDING_PAYMENT: "bg-yellow-100 text-yellow-800",
  PENDING: "bg-yellow-100 text-yellow-800",
  IN_USE: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  REFUNDED: "bg-blue-100 text-blue-800",
  OUT_OF_SERVICE: "bg-red-100 text-red-800",
  FAILED: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-700",
  EXPIRED: "bg-gray-100 text-gray-700",
};

export function statusClass(status: string): string {
  return `inline-block rounded px-2 py-0.5 text-xs font-semibold ${
    STATUS_COLOURS[status] ?? "bg-gray-100 text-gray-700"
  }`;
}

/** Value for an <input type="date"> in the browser's time zone. */
export function toDateInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}`;
}

/** Date and time inputs for the next full hour, in the browser's time zone. */
export function nextHourDefaults(): { date: string; time: string } {
  const next = new Date();
  next.setHours(next.getHours() + 1, 0, 0, 0);
  return {
    date: toDateInputValue(next),
    time: `${String(next.getHours()).padStart(2, "0")}:00`,
  };
}

/** Combine a date input and a time input (local time) into a Date. */
export function localDateTime(date: string, time: string): Date {
  return new Date(`${date}T${time}`);
}
