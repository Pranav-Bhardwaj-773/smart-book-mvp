"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Book, BookList, Dashboard } from "@/lib/types";
import { BookAvatar } from "@/components/book-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
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
    <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Catalog</h1>
        <p className="text-sm text-muted-foreground">
          Search the shelf and rent a book.
        </p>
      </div>

      <form onSubmit={onSearch} className="flex flex-col gap-3">
        <div className="flex gap-2">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search books, authors, or topics"
            className="h-10"
          />
          <Button type="submit" className="h-10 px-4">
            Search
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <NativeSelect value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="relevance">Relevance</option>
            <option value="title_asc">Title A–Z</option>
            <option value="title_desc">Title Z–A</option>
            <option value="year_new">Newest year</option>
            <option value="year_old">Oldest year</option>
            <option value="availability">Availability</option>
          </NativeSelect>
          <NativeSelect
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">All languages</option>
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
          </NativeSelect>
          <label className="flex h-8 cursor-pointer items-center gap-2 rounded-lg border border-input px-2.5 text-sm">
            <input
              type="checkbox"
              className="size-3.5 accent-current"
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

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {msg && (
        <p className="text-sm text-muted-foreground" role="status">
          {msg}
        </p>
      )}
      {data?.message && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
          {data.message}
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        {data?.total ?? 0} books · page {data?.page ?? 1} of {totalPages}
      </p>

      <ul className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {data?.items.map((b) => {
          const hasThis = dash?.current.some((r) => r.book_id === b.id);
          const atLimit = (dash?.active_count ?? 0) >= (dash?.max_allowed ?? 2);
          const blocked =
            b.status === "archived" ||
            b.available_copies <= 0 ||
            Boolean(user && (hasThis || atLimit));
          return (
            <li key={b.id}>
              <Card className="gap-0 py-0">
                <div className="flex gap-3 p-4 lg:flex-col">
                  <BookAvatar title={b.title} coverUrl={b.cover_url} className="lg:size-16" />
                  <div className="min-w-0 flex-1">
                    <h2 className="font-medium leading-snug max-lg:truncate lg:line-clamp-2">{b.title}</h2>
                    <p className="truncate text-sm text-muted-foreground">{b.authors}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {b.category ? (
                        <Badge variant="outline">{b.category}</Badge>
                      ) : null}
                      <Badge variant="outline">{b.publication_year}</Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-2 border-t px-4 py-3 lg:flex-col lg:items-stretch">
                  <p className="text-xs text-muted-foreground">
                    {b.status.replaceAll("_", " ")} · {b.available_copies} available
                  </p>
                  <div className="flex shrink-0 gap-2 lg:justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      nativeButton={false}
                      render={<Link href={`/books/${b.id}`} />}
                    >
                      Details
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={Boolean(user && blocked)}
                      onClick={() => rentFromCard(b)}
                    >
                      Rent
                    </Button>
                  </div>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>

      {data && data.items.length === 0 && (
        <p className="rounded-xl border px-4 py-8 text-center text-sm text-muted-foreground">
          No books match this search.
        </p>
      )}

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
