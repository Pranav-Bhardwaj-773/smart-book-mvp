import { getToken } from "./auth-store";

const DEFAULT_LOCAL = "http://127.0.0.1:8000";

/** Public HTTPS API URL safe to call from the browser (Render, etc.). */
function browserDirectApi(): string | null {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) return null;
  const url = raw.replace(/\/$/, "");
  if (!/^https:\/\//i.test(url)) return null;
  if (/^https:\/\/(127\.0\.0\.1|localhost)/i.test(url)) return null;
  return url;
}

/**
 * Browser: prefer same-origin `/backend` proxy, or NEXT_PUBLIC_API_URL if set.
 * Server: BACKEND_URL / NEXT_PUBLIC_API_URL / localhost.
 */
function apiBase(): string {
  if (typeof window !== "undefined") {
    const direct = browserDirectApi();
    if (direct) return direct;
    return "/backend";
  }
  const direct =
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    DEFAULT_LOCAL;
  return direct.replace(/\/$/, "");
}

function token() {
  if (typeof window === "undefined") return null;
  return getToken();
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);

  const res = await fetch(`${apiBase()}${path}`, { ...init, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : res.statusText;
    throw new Error(message);
  }
  return data as T;
}

export const api = {
  register: (body: object) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: object) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<import("./types").User>("/auth/me"),
  books: (opts: {
    q?: string;
    page?: number;
    sort?: string;
    language?: string;
    available_only?: boolean;
  }) => {
    const p = new URLSearchParams();
    p.set("q", opts.q ?? "");
    p.set("page", String(opts.page ?? 1));
    p.set("page_size", "12");
    p.set("sort", opts.sort ?? "relevance");
    if (opts.language) p.set("language", opts.language);
    if (opts.available_only) p.set("available_only", "true");
    return request<import("./types").BookList>(`/books?${p.toString()}`);
  },
  book: (id: number) => request<import("./types").Book>(`/books/${id}`),
  dashboard: () => request<import("./types").Dashboard>("/rentals/me"),
  rent: (book_id: number) =>
    request("/rentals", { method: "POST", body: JSON.stringify({ book_id }) }),
  returnBook: (id: number) =>
    request(`/rentals/${id}/return`, { method: "POST" }),
  adminStats: () => request("/admin/stats"),
  adminUsers: (q = "") =>
    request<import("./types").User[]>(
      `/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  adminSetStatus: (id: number, status: string) =>
    request(`/admin/users/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  adminBooks: () => request<import("./types").Book[]>("/admin/books"),
  adminArchive: (id: number) =>
    request(`/admin/books/${id}/archive`, { method: "POST" }),
  adminRestore: (id: number) =>
    request(`/admin/books/${id}/restore`, { method: "POST" }),
  adminInventory: (id: number, delta: number) =>
    request(`/admin/books/${id}/inventory`, {
      method: "POST",
      body: JSON.stringify({ delta }),
    }),
  adminRentals: (status = "") =>
    request(
      `/admin/rentals${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  adminReturn: (id: number) =>
    request(`/admin/rentals/${id}/return`, { method: "POST" }),
  adminAddBook: (body: object) =>
    request("/admin/books", { method: "POST", body: JSON.stringify(body) }),
};
