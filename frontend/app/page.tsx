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
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/components/auth-provider";

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<BookList | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(nextPage = page, query = q) {
    setError("");
    setLoading(true);
    try {
      const list = await api.books({
        q: query,
        page: nextPage,
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
      setError(
        e instanceof Error
          ? e.message
          : "We could not complete your search. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(1, q);
  }, [user]);

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

  const totalPages = Math.max(
    1,
    Math.ceil((data?.total ?? 0) / (data?.page_size ?? 12)),
  );

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
            placeholder="Search what you like to read"
            className="h-10"
          />
          <Button type="submit" className="h-10 px-4" disabled={loading}>
            {loading && <Spinner data-icon="inline-start" />}
            Search
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

      {loading ? (
        <div
          className="flex flex-col items-center justify-center gap-3 py-16"
          role="status"
          aria-live="polite"
        >
          <Spinner className="size-8" />
          <p className="text-sm text-muted-foreground">Searching books…</p>
        </div>
      ) : (
        <>
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
                      <BookAvatar
                        title={b.title}
                        coverUrl={b.cover_url}
                        className="lg:size-16"
                      />
                      <div className="min-w-0 flex-1">
                        <h2 className="font-medium leading-snug max-lg:truncate lg:line-clamp-2">
                          {b.title}
                        </h2>
                        <p className="truncate text-sm text-muted-foreground">
                          {b.authors}
                        </p>
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
                        {b.status.replaceAll("_", " ")} · {b.available_copies}{" "}
                        available
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
              disabled={page <= 1 || loading}
              onClick={() => load(page - 1, q)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={page >= totalPages || loading}
              onClick={() => load(page + 1, q)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}