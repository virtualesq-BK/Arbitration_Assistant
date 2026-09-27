const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, ...rest } = options;
  const isForm = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const headers: Record<string, string> = {
    // For multipart uploads the browser must set the boundary itself.
    ...(isForm ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((rest.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${API_BASE}/api/v1${path}`, { ...rest, headers });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 401 && typeof window !== "undefined") {
      window.dispatchEvent(new Event("arbiconstruct:unauthorized"));
    }
    throw new ApiError(res.status, `API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const match = err.message.match(/"detail"\s*:\s*"([^"]+)"/);
    return match ? match[1] : err.message;
  }
  if (err instanceof Error) return err.message;
  return "Unexpected error";
}
