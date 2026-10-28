"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Book, BookList, Dashboard } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/auth-provider";

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("relevance");
  const [language, setLanguage] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<BookList | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  async function load(nextPage = page, query = q) {
    setError("");
    try {
      const list = await api.books({
        q: query,
        page: nextPage,
        sort,
        language: language || undefined,
        available_only: availableOnly,
      });
      setData(list);
      setPage(nextPage);
      if (user) {
        try {
          setDash(await api.dashboard());
        } catch {
          setDash(null);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "We could not complete your search. Please try again.");
    }
  }

  useEffect(() => {
    load(1, q);
  }, [sort, language, availableOnly, user]);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    load(1, q);
  }

  async function rentFromCard(b: Book) {
    if (!user) {
      router.push(`/login?next=/books/${b.id}`);
      return;
    }
    try {
      await api.rent(b.id);
      setMsg("Book rented successfully.");
      await load(page, q);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Rent failed");
    }
  }

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 12)));

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <form onSubmit={onSearch} className="flex flex-col gap-3">
        <div className="flex gap-2">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search naturally, for example: beginner books about artificial intelligence"
          />
          <Button type="submit">Search</Button>
        </div>
        <div className="flex flex-wrap gap-2 items-center text-sm">
          <select
            className="border rounded h-8 px-2"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="relevance">Relevance</option>
            <option value="title_asc">Title A–Z</option>
            <option value="title_desc">Title Z–A</option>
            <option value="year_new">Newest year</option>
            <option value="year_old">Oldest year</option>
            <option value="availability">Availability</option>
          </select>
          <select
            className="border rounded h-8 px-2"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">All languages</option>
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
          </select>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={availableOnly}
              onChange={(e) => setAvailableOnly(e.target.checked)}
            />
            Available only
          </label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setLanguage("");
              setAvailableOnly(false);
              setSort("relevance");
            }}
          >
            Clear filters
          </Button>
        </div>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {msg && <p className="text-sm">{msg}</p>}
      {data?.message && <p className="text-sm text-amber-700">{data.message}</p>}
      <p className="text-sm text-muted-foreground">
        {data?.total ?? 0} books · page {data?.page ?? 1} of {totalPages}
      </p>

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((b) => {
          const hasThis = dash?.current.some((r) => r.book_id === b.id);
          const atLimit = (dash?.active_count ?? 0) >= (dash?.max_allowed ?? 2);
          const blocked =
            b.status === "archived" ||
            b.available_copies <= 0 ||
            Boolean(user && (hasThis || atLimit));
          return (
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
                {b.status.replaceAll("_", " ")} · {b.available_copies} available
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  nativeButton={false}
                  render={<Link href={`/books/${b.id}`} />}
                >
                  View details
                </Button>
                <Button
                  size="sm"
                  disabled={Boolean(user && blocked)}
                  onClick={() => rentFromCard(b)}
                >
                  {!user ? "Please sign in to rent this book." : "Rent"}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="flex justify-center gap-2">
        <Button
          variant="outline"
          disabled={page <= 1}
          onClick={() => load(page - 1, q)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          disabled={page >= totalPages}
          onClick={() => load(page + 1, q)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}