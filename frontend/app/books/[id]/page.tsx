"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Book } from "@/lib/types";
import { Button } from "@/components/ui/button";

export default function BookPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [book, setBook] = useState<Book | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.book(Number(id)).then(setBook).catch((e) => setMsg(e.message));
  }, [id]);

  async function rent() {
    if (!localStorage.getItem("token")) {
      router.push(`/login?next=/books/${id}`);
      return;
    }
    try {
      await api.rent(Number(id));
      setMsg("Book rented successfully.");
      setBook(await api.book(Number(id)));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Rent failed");
    }
  }

  if (!book) return <p className="p-6">{msg || "Loading…"}</p>;

  const canRent =
    book.status !== "archived" && book.available_copies > 0;

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
      <Button onClick={rent} disabled={!canRent}>
        {canRent ? "Rent" : "Unavailable"}
      </Button>
      {msg && <p className="text-sm">{msg}</p>}
    </div>
  );
}