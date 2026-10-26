export class ApiError extends Error {
  constructor(public status: number) {
    super(
      status === 401
        ? "Please sign in again."
        : status === 403
          ? "This action is not available for your account."
          : "The request could not be completed. Check your input or try again.",
    );
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "include",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event("urumi:expired"));
    throw new ApiError(response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export type User = {
  id: string;
  username: string;
  role: "admin" | "member";
  enabled?: boolean;
};
export type Key = {
  id: string;
  label: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
};
export type Tool = {
  name: string;
  description?: string;
  input_schema?: unknown;
};
export type Server = {
  id: string;
  slug: string;
  display_name: string;
  url: string;
  enabled: boolean;
  observed_status: string;
  has_credential: boolean;
  last_checked: string | null;
  tools: Tool[];
  tools_stale: boolean;
};
export type Audit = {
  id: string;
  username: string;
  server_slug: string | null;
  gateway_tool: string;
  started_at: string;
  duration_ms: number | null;
  outcome: string;
  error_code: string | null;
};
export type Trace = {
  tool: string;
  server: string;
  outcome: string;
  duration_ms: number;
  summary: string;
};
export type Answer = { answer: string; trace: Trace[]; error: string | null };
