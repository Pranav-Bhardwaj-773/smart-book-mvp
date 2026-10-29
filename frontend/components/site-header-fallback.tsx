import Link from "next/link";
import { BookOpen } from "lucide-react";

/** Static shell for prerender; replaced once SiteHeader resolves the pathname. */
export function SiteHeaderFallback() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between gap-3 px-4">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2 font-semibold tracking-tight"
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border bg-linear-to-br from-card to-muted">
            <BookOpen className="size-4" />
          </span>
          <span className="truncate">Smart Book</span>
        </Link>
        <div className="flex h-9 flex-1 max-w-md items-center justify-end gap-2 lg:max-w-none">
          <div className="hidden h-9 w-48 animate-pulse rounded-md bg-muted lg:block" />
          <div className="size-9 shrink-0 animate-pulse rounded-md bg-muted" />
          <div className="size-9 shrink-0 animate-pulse rounded-md bg-muted lg:hidden" />
        </div>
      </div>
    </header>
  );
}
