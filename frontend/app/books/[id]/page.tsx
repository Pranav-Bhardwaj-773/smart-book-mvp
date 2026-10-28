"use client";

import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Book, Dashboard } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

function BookPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user, ready } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    const b = await api.book(Number(id));
    setBook(b);
    if (user) {
      try {
        setDash(await api.dashboard());
      } catch {
        setDash(null);
      }
    } else {
      setDash(null);
    }
  }

  useEffect(() => {
    if (!ready) return;
    load().catch((e) => setMsg(e.message));
  }, [id, ready, user]);

  async function rent() {
    if (!user) {
      router.push(`/login?next=/books/${id}`);
      return;
    }
    try {
      await api.rent(Number(id));
      setMsg("Book rented successfully.");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Rent failed");
    }
  }

  if (!book) return <p className="p-6">{msg || "Loading…"}</p>;

  const archived = book.status === "archived";
  const noCopies = book.available_copies <= 0;
  const hasThis =
    dash?.current.some((r) => r.book_id === book.id) ?? false;
  const atLimit = (dash?.active_count ?? 0) >= (dash?.max_allowed ?? 2);

  let reason = "";
  if (archived) reason = "This book is no longer available for rental.";
  else if (noCopies) reason = "This book is currently unavailable.";
  else if (user && hasThis) reason = "You already have an active rental for this book.";
  else if (user && atLimit) {
    reason =
      "You already have two active rentals. Please return one of your books before renting another.";
  }

  const disabled = Boolean(user && reason);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">{book.title}</h1>
      <p>{book.authors}</p>
      <p>{book.description}</p>
      <p>
        {book.language} · {book.publication_year} · {book.page_count} pages ·{" "}
        {book.reading_level}
      </p>
      <p>
        Availability: {book.status.replaceAll("_", " ")} (
        {book.available_copies} of {book.total_copies})
      </p>
      {dash && <p className="text-sm">{dash.capacity_message}</p>}
      <Button onClick={rent} disabled={disabled}>
        {!user ? "Sign in to rent" : disabled ? "Cannot rent" : "Rent"}
      </Button>
      {(reason || msg) && <p className="text-sm">{msg || reason}</p>}
    </div>
  );
}

export default function BookPageRoute() {
  return (
    <Suspense fallback={<p className="p-6">Loading…</p>}>
      <BookPage />
    </Suspense>
  );
}