/**
 * Typed API client.
 *
 * Every view previously called `fetch` and checked `r.ok` inline, so backend
 * error messages were discarded and replaced with a generic string. This
 * surfaces the server's own `detail` and distinguishes an expired session
 * from a genuine failure.
 */

export const TOKEN_STORAGE_KEY = "jobpilot-token";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** The session is gone or invalid — the caller should sign the user out. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** Sent as-is (FormData); skips JSON encoding and the content-type header. */
  formData?: FormData;
  signal?: AbortSignal;
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    if (Array.isArray(payload?.detail)) {
      // FastAPI request-validation errors arrive as a list of field errors.
      return payload.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ");
    }
  } catch {
    // Non-JSON error body (a proxy error page, say) — fall through.
  }
  return `Erro ${response.status}`;
}

export function createClient(token: string) {
  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (!options.formData) headers["Content-Type"] = "application/json";

    let response: Response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method: options.method ?? "GET",
        headers,
        body: options.formData ?? (options.body ? JSON.stringify(options.body) : undefined),
        signal: options.signal,
      });
    } catch {
      throw new ApiError("Sem conexão com o servidor.", 0);
    }

    if (!response.ok) throw new ApiError(await readError(response), response.status);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
    post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
    patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
    upload: <T>(path: string, formData: FormData) =>
      request<T>(path, { method: "POST", formData }),
  };
}

export type ApiClient = ReturnType<typeof createClient>;
