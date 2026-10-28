"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BookOpen, Menu, Moon, Sun, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("smartbook-theme");
    const next = stored ? stored === "dark" : true;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
  }, []);

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("smartbook-theme", next ? "dark" : "light");
    setDark(next);
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? <Sun /> : <Moon />}
    </Button>
  );
}

export function SiteHeader() {
  const router = useRouter();
  const { user, ready, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [pathname, setPathname] = useState("");

  useEffect(() => {
    const sync = () => setPathname(window.location.pathname);
    sync();
    window.addEventListener("popstate", sync);
    const push = history.pushState.bind(history);
    const replace = history.replaceState.bind(history);
    history.pushState = (...args: Parameters<History["pushState"]>) => {
      push(...args);
      sync();
    };
    history.replaceState = (...args: Parameters<History["replaceState"]>) => {
      replace(...args);
      sync();
    };
    return () => {
      window.removeEventListener("popstate", sync);
      history.pushState = push;
      history.replaceState = replace;
    };
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function onLogout() {
    logout();
    setOpen(false);
    router.push("/");
  }

  function navLink(href: string, label: string, mobile: boolean) {
    const active = pathname === href;
    return (
      <Button
        key={href}
        variant={active ? "secondary" : "ghost"}
        className={mobile ? "h-10 w-full justify-start px-3" : undefined}
        nativeButton={false}
        render={<Link href={href} />}
      >
        {label}
      </Button>
    );
  }

  function links(mobile: boolean) {
    return (
      <>
        {navLink("/", "Catalog", mobile)}
        {ready && user && navLink("/dashboard", "My rentals", mobile)}
        {ready && user?.role === "admin" && navLink("/admin", "Admin", mobile)}
        {ready && user ? (
          <>
            <span
              className={
                mobile
                  ? "px-3 py-1 text-sm text-muted-foreground"
                  : "max-w-36 truncate px-2 text-sm text-muted-foreground"
              }
            >
              {user.full_name}
            </span>
            <Button
              variant="outline"
              className={mobile ? "h-10 w-full" : undefined}
              onClick={onLogout}
            >
              Sign out
            </Button>
          </>
        ) : ready ? (
          <>
            <Button
              variant="ghost"
              className={mobile ? "h-10 w-full justify-start px-3" : undefined}
              nativeButton={false}
              render={<Link href="/login" />}
            >
              Sign in
            </Button>
            <Button
              className={mobile ? "h-10 w-full" : undefined}
              nativeButton={false}
              render={<Link href="/register" />}
            >
              Register
            </Button>
          </>
        ) : null}
      </>
    );
  }

  return (
    <>
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between gap-3 px-4">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2 font-semibold tracking-tight"
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full border bg-card">
            <BookOpen className="size-4" />
          </span>
          <span className="truncate">Smart Book</span>
        </Link>

        <div className="flex items-center gap-1">
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
            {links(false)}
          </nav>
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X /> : <Menu />}
          </Button>
        </div>
      </div>

      {open && (
        <nav
          id="mobile-nav"
          aria-label="Mobile"
          className="absolute inset-x-0 top-full z-40 max-h-[calc(100vh-3.5rem)] overflow-y-auto border-b bg-background px-3 py-3 lg:hidden"
        >
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-1">
            {links(true)}
          </div>
        </nav>
      )}
    </header>
    {open && (
      <button
        type="button"
        aria-label="Close menu"
        className="fixed inset-0 top-14 z-30 bg-black/50 lg:hidden"
        onClick={() => setOpen(false)}
      />
    )}
    </>
  );
}
