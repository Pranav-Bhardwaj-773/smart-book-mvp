"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookMarked,
  Library,
  Search,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Book, BookList, Dashboard } from "@/lib/types";
import { CatalogBookCard } from "@/components/catalog-book-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/components/auth-provider";

const QUICK_SEARCHES = [
  "Jane Austen",
  "Mystery",
  "Science fiction",
  "Classic literature",
];

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("relevance");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [data, setData] = useState<BookList | null>(null);
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(
    nextPage = page,
    query = q,
    nextSort = sort,
    onlyAvailable = availableOnly,
  ) {
    setError("");
    setLoading(true);
    try {
      const list = await api.books({
        q: query,
        page: nextPage,
        sort: nextSort,
        available_only: onlyAvailable,
      });
      setData(list);
      setPage(nextPage);
      setSort(nextSort);
      setAvailableOnly(onlyAvailable);
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
    load(1, q, sort, availableOnly);
  }, [user]);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    load(1, q, sort, availableOnly);
  }

  function quickSearch(term: string) {
    setQ(term);
    load(1, term, sort, availableOnly);
  }

  async function rentFromCard(b: Book) {
    if (!user) {
      router.push(`/login?next=/books/${b.id}`);
      return;
    }
    try {
      await api.rent(b.id);
      setMsg("Book rented successfully.");
      await load(page, q, sort, availableOnly);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Rent failed");
    }
  }

  const totalPages = Math.max(
    1,
    Math.ceil((data?.total ?? 0) / (data?.page_size ?? 12)),
  );

  return (
    <>
      <section className="catalog-hero relative overflow-hidden border-b">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,oklch(0.55_0.12_260/0.22),transparent)] dark:bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,oklch(0.65_0.14_260/0.18),transparent)]"
          aria-hidden
        />
        <div className="pointer-events-none absolute -left-24 top-20 size-72 rounded-full bg-primary/5 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 top-32 size-64 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative mx-auto w-full max-w-7xl px-4 pb-14 pt-12 lg:pb-20 lg:pt-16">
          <div className="mx-auto max-w-3xl text-center">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-border/80 bg-background/60 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur-sm">
              <Sparkles className="size-3.5 text-amber-500" />
              Your digital library, simplified
            </p>
            <h1 className="font-serif text-4xl font-normal tracking-tight text-balance sm:text-5xl lg:text-6xl">
              Discover your next great read
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Search {data?.total ? `${data.total}+` : "our"} titles in plain
              language, explore classics and new favorites, and rent in seconds.
            </p>
          </div>

          <form
            onSubmit={onSearch}
            className="mx-auto mt-10 max-w-2xl"
            role="search"
          >
            <div className="flex flex-col gap-2 rounded-2xl border border-border/80 bg-card/80 p-2 shadow-lg shadow-black/5 ring-1 ring-foreground/[0.04] backdrop-blur-sm sm:flex-row sm:items-center dark:shadow-black/30">
              <div className="relative min-w-0 flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Try “Victorian romance” or an author name…"
                  className="h-12 border-0 bg-transparent pl-10 shadow-none focus-visible:ring-0"
                  aria-label="Search books"
                />
              </div>
              <Button
                type="submit"
                className="h-12 shrink-0 rounded-xl px-6 sm:min-w-28"
                disabled={loading}
              >
                {loading && <Spinner data-icon="inline-start" />}
                Search
              </Button>
            </div>
          </form>

          <div className="mx-auto mt-5 flex max-w-2xl flex-wrap items-center justify-center gap-2">
            <span className="text-xs text-muted-foreground">Popular:</span>
            {QUICK_SEARCHES.map((term) => (
              <button
                key={term}
                type="button"
                onClick={() => quickSearch(term)}
                className="rounded-full border border-border/70 bg-background/50 px-3 py-1 text-xs text-muted-foreground transition hover:border-border hover:bg-muted hover:text-foreground"
              >
                {term}
              </button>
            ))}
          </div>

          <div className="mx-auto mt-12 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              {
                icon: Library,
                title: "Curated catalog",
                text: "Fiction, classics, and more in one place.",
              },
              {
                icon: Search,
                title: "Natural search",
                text: "Describe what you want—not just exact titles.",
              },
              {
                icon: BookMarked,
                title: "Simple rentals",
                text: "Reserve a copy and pick up when you're ready.",
              },
            ].map(({ icon: Icon, title, text }) => (
              <div
                key={title}
                className="rounded-xl border border-border/60 bg-background/40 px-4 py-4 text-center backdrop-blur-sm"
              >
                <Icon className="mx-auto mb-2 size-5 text-primary/80" />
                <p className="text-sm font-medium">{title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto w-full max-w-7xl space-y-6 px-4 py-10">
        <div
          id="catalog"
          className="flex flex-col gap-4 border-b border-border/60 pb-6 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <h2 className="font-heading text-2xl font-semibold tracking-tight">
              Browse the shelf
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {loading
                ? "Loading titles…"
                : `${data?.total ?? 0} books · page ${data?.page ?? 1} of ${totalPages}`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                checked={availableOnly}
                onChange={(e) => load(1, q, sort, e.target.checked)}
                className="size-4 rounded border-input accent-primary"
              />
              Available now
            </label>
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="size-4 text-muted-foreground" />
              <NativeSelect
                value={sort}
                onChange={(e) => load(1, q, e.target.value, availableOnly)}
                className="h-9 min-w-[140px] bg-background"
                aria-label="Sort books"
              >
                <option value="relevance">Relevance</option>
                <option value="title_asc">Title A–Z</option>
                <option value="year_new">Newest year</option>
                <option value="availability">Most available</option>
              </NativeSelect>
            </div>
          </div>
        </div>

        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {msg && (
          <p
            className="rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground"
            role="status"
          >
            {msg}
          </p>
        )}
        {data?.message && (
          <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
            {data.message}
          </p>
        )}

        {loading ? (
          <div
            className="flex flex-col items-center justify-center gap-3 py-24"
            role="status"
            aria-live="polite"
          >
            <Spinner className="size-8" />
            <p className="text-sm text-muted-foreground">Searching books…</p>
          </div>
        ) : (
          <>
            <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {data?.items.map((b) => {
                const hasThis = dash?.current.some((r) => r.book_id === b.id);
                const atLimit =
                  (dash?.active_count ?? 0) >= (dash?.max_allowed ?? 2);
                const blocked =
                  b.status === "archived" ||
                  b.available_copies <= 0 ||
                  Boolean(user && (hasThis || atLimit));
                return (
                  <li key={b.id} className="min-h-0">
                    <CatalogBookCard
                      book={b}
                      rentDisabled={Boolean(user && blocked)}
                      onRent={() => rentFromCard(b)}
                    />
                  </li>
                );
              })}
            </ul>

            {data && data.items.length === 0 && (
              <div className="rounded-2xl border border-dashed px-6 py-16 text-center">
                <p className="font-medium">No books match this search</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Try a different phrase or clear filters to see more titles.
                </p>
                <Button
                  variant="outline"
                  className="mt-6"
                  onClick={() => {
                    setQ("");
                    load(1, "", sort, false);
                  }}
                >
                  Clear search
                </Button>
              </div>
            )}

            {data && data.items.length > 0 && (
              <nav
                className="flex flex-col items-center gap-3 pt-4 sm:flex-row sm:justify-center"
                aria-label="Pagination"
              >
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={page <= 1 || loading}
                    onClick={() => load(page - 1, q, sort, availableOnly)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    disabled={page >= totalPages || loading}
                    onClick={() => load(page + 1, q, sort, availableOnly)}
                  >
                    Next
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
              </nav>
            )}
          </>
        )}
      </div>
    </>
  );
}
