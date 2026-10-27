"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookList } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function HomePage() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<BookList | null>(null);
  const [error, setError] = useState("");

  async function load(query = "") {
    setError("");
    try {
      setData(await api.books(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    load(q);
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <form onSubmit={onSearch} className="flex gap-2">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search naturally, for example: beginner books about artificial intelligence"
        />
        <Button type="submit">Search</Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {data?.message && <p className="text-sm text-amber-700">{data.message}</p>}
      <p className="text-sm text-muted-foreground">{data?.total ?? 0} books</p>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((b) => (
          <li key={b.id} className="border rounded-lg p-3 space-y-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={b.cover_url ?? ""}
              alt={`Cover of ${b.title}`}
              className="w-full h-48 object-cover rounded"
            />
            <h2 className="font-medium">{b.title}</h2>
            <p className="text-sm">{b.authors}</p>
            <p className="text-sm">
              {b.status.replace("_", " ")} · {b.available_copies} available
            </p>
            <Link href={`/books/${b.id}`} className="text-sm underline">
              View details
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}