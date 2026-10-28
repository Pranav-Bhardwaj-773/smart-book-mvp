export const AUTH_EVENT = "smartbook-auth";

export function getToken() {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) sessionStorage.setItem("token", token);
  else sessionStorage.removeItem("token");
  window.dispatchEvent(new Event(AUTH_EVENT));
}