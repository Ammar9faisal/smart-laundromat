import { supabase } from "@/lib/supabase";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/**
 * Calls the FastAPI backend. Sends the signed-in user's Supabase access token
 * when there is one, and throws ApiError with a readable message on failure.
 */
export async function api<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {};

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body:
        options.body === undefined
          ? undefined
          : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError(
      0,
      "Cannot reach the server. Make sure the backend is running."
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(data, response.status),
      data
    );
  }

  return data as T;
}

function errorMessage(data: unknown, status: number): string {
  const detail = (data as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  // FastAPI validation errors: a list of { msg, loc, ... }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) =>
        String((item as { msg?: string }).msg ?? "Invalid input").replace(
          /^Value error, /,
          ""
        )
      )
      .join(". ");
  }

  if (status === 401) return "Please log in to continue.";
  if (status === 403) return "You do not have permission to do that.";

  return `Request failed (${status})`;
}

export function errorText(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}
