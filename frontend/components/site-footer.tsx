import Link from "next/link";
import { BookOpen } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t bg-muted/30">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <span className="flex size-8 items-center justify-center rounded-lg border bg-background">
            <BookOpen className="size-4" />
          </span>
          Smart Book
        </div>
        <p className="max-w-md text-sm text-muted-foreground">
          Browse hundreds of titles, search in plain language, and rent books in
          a few clicks.
        </p>
        <nav className="flex flex-wrap gap-4 text-sm" aria-label="Footer">
          <Link
            href="/"
            className="text-muted-foreground transition hover:text-foreground"
          >
            Catalog
          </Link>
          <Link
            href="/login"
            className="text-muted-foreground transition hover:text-foreground"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="text-muted-foreground transition hover:text-foreground"
          >
            Register
          </Link>
        </nav>
      </div>
    </footer>
  );
}
