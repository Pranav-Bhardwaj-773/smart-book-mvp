"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(!!localStorage.getItem("token"));
  }, []);

  function logout() {
    localStorage.removeItem("token");
    setLoggedIn(false);
    router.push("/");
    router.refresh();
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
        {loggedIn ? (
          <>
            <Button
              variant="ghost"
              nativeButton={false}
              render={<Link href="/dashboard" />}
            >
              My rentals
            </Button>
            <Button variant="outline" onClick={logout}>
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