"use client";

import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Book, Dashboard } from "@/lib/types";
import { BookAvatar } from "@/components/book-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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

  if (!book) {
    return (
      <p className="mx-auto max-w-2xl px-4 py-8 text-sm text-muted-foreground">
        {msg || "Loading…"}
      </p>
    );
  }

  const archived = book.status === "archived";
  const noCopies = book.available_copies <= 0;
  const hasThis = dash?.current.some((r) => r.book_id === book.id) ?? false;
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
    <div className="mx-auto w-full max-w-2xl space-y-4 px-4 py-6">
      <Card className="gap-0 py-0">
        <div className="flex gap-4 p-4">
          <BookAvatar
            title={book.title}
            coverUrl={book.cover_url}
            className="size-16 text-base"
          />
          <div className="min-w-0 flex-1 space-y-2">
            <h1 className="text-xl font-semibold tracking-tight">{book.title}</h1>
            <p className="text-sm text-muted-foreground">{book.authors}</p>
            <div className="flex flex-wrap gap-1.5">
              {book.category ? <Badge variant="outline">{book.category}</Badge> : null}
              <Badge variant="outline">{book.language}</Badge>
              <Badge variant="outline">{book.publication_year}</Badge>
              <Badge variant="outline">{book.page_count} pages</Badge>
              {book.reading_level ? (
                <Badge variant="outline">{book.reading_level}</Badge>
              ) : null}
            </div>
          </div>
        </div>
        <div className="border-t px-4 py-4">
          <p className="text-sm leading-relaxed">{book.description}</p>
        </div>
        <div className="flex flex-col gap-3 border-t px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            {book.status.replaceAll("_", " ")} · {book.available_copies} of{" "}
            {book.total_copies} available
          </p>
          <Button variant="outline" onClick={rent} disabled={disabled}>
            {!user ? "Sign in to rent" : disabled ? "Cannot rent" : "Rent"}
          </Button>
        </div>
      </Card>
      {dash && <p className="text-sm text-muted-foreground">{dash.capacity_message}</p>}
      {(reason || msg) && (
        <p className="text-sm text-muted-foreground" role="status">
          {msg || reason}
        </p>
      )}
    </div>
  );
}

export default function BookPageRoute() {
  return (
    <Suspense
      fallback={
        <p className="mx-auto max-w-2xl px-4 py-8 text-sm text-muted-foreground">
          Loading…
        </p>
      }
    >
      <BookPage />
    </Suspense>
  );
}
