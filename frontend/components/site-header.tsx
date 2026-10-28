"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

export function SiteHeader() {
  const router = useRouter();
  const { user, ready, logout } = useAuth();

  function onLogout() {
    logout();
    router.push("/");
  }

  return (
    <header className="border-b px-4 py-3 flex items-center justify-between gap-4">
      <Link href="/" className="font-semibold">
        Smart Book
      </Link>
      <nav className="flex items-center gap-2">
        <Button variant="ghost" nativeButton={false} render={<Link href="/" />}>
          Catalog
        </Button>
        {!ready ? null : user ? (
          <>
            <Button
              variant="ghost"
              nativeButton={false}
              render={<Link href="/dashboard" />}
            >
              My rentals
            </Button>
            {user.role === "admin" && (
              <Button
                variant="ghost"
                nativeButton={false}
                render={<Link href="/admin" />}
              >
                Admin
              </Button>
            )}
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user.full_name}
            </span>
            <Button variant="outline" onClick={onLogout}>
              Sign out
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="ghost"
              nativeButton={false}
              render={<Link href="/login" />}
            >
              Sign in
            </Button>
            <Button nativeButton={false} render={<Link href="/register" />}>
              Register
            </Button>
          </>
        )}
      </nav>
    </header>
  );
}