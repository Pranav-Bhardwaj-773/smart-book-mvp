const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function token() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);

  const res = await fetch(`${API}${path}`, { ...init, headers });
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
  me: () => request("/auth/me"),
  books: (q: string, page = 1) =>
    request<import("./types").BookList>(
      `/books?q=${encodeURIComponent(q)}&page=${page}&page_size=12`
    ),
  book: (id: number) => request<import("./types").Book>(`/books/${id}`),
  dashboard: () => request<import("./types").Dashboard>("/rentals/me"),
  rent: (book_id: number) =>
    request("/rentals", { method: "POST", body: JSON.stringify({ book_id }) }),
  returnBook: (id: number) =>
    request(`/rentals/${id}/return`, { method: "POST" }),
};