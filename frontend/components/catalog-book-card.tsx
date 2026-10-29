"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { BookAvatar } from "@/components/book-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Book } from "@/lib/types";
import { cn } from "cn";

function availabilityMeta(book: Book) {
  if (book.status === "archived") {
    return { label: "Archived", className: "bg-muted text-muted-foreground" };
  }
  if (book.available_copies <= 0) {
    return {
      label: "Out of stock",
      className: "bg-destructive/15 text-destructive",
    };
  }
  if (book.available_copies < book.total_copies) {
    return {
      label: `${book.available_copies} left`,
      className: "bg-amber-500/15 text-amber-800 dark:text-amber-200",
    };
  }
  return {
    label: "Available",
    className: "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200",
  };
}

export function CatalogBookCard({
  book,
  rentDisabled,
  onRent,
}: {
  book: Book;
  rentDisabled: boolean;
  onRent: () => void;
}) {
  const status = availabilityMeta(book);

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card/90 shadow-sm ring-1 ring-foreground/[0.04] transition duration-300 hover:-translate-y-0.5 hover:border-border hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/25">
      <Link
        href={`/books/${book.id}`}
        className="relative flex flex-col items-center bg-linear-to-b from-muted/50 to-transparent px-5 pb-4 pt-6"
      >
        <span
          className={cn(
            "absolute right-3 top-3 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            status.className,
          )}
        >
          {status.label}
        </span>
        <div className="w-full max-w-[132px] transition-transform duration-300 group-hover:scale-[1.04]">
          <BookAvatar
            title={book.title}
            coverUrl={book.cover_url}
            variant="cover"
          />
        </div>
      </Link>

      <div className="flex flex-1 flex-col gap-3 px-5 pb-5 pt-1">
        <div className="space-y-1">
          <h2 className="font-heading line-clamp-2 text-base leading-snug font-medium tracking-tight">
            <Link
              href={`/books/${book.id}`}
              className="hover:text-primary/90 hover:underline hover:underline-offset-2"
            >
              {book.title}
            </Link>
          </h2>
          <p className="line-clamp-1 text-sm text-muted-foreground">
            {book.authors}
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {book.category ? (
            <Badge variant="secondary" className="rounded-md font-normal">
              {book.category}
            </Badge>
          ) : null}
          <Badge variant="outline" className="rounded-md font-normal">
            {book.publication_year}
          </Badge>
        </div>

        <div className="mt-auto flex items-center gap-2 pt-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-9 flex-1 justify-between px-3 text-muted-foreground hover:text-foreground"
            nativeButton={false}
            render={<Link href={`/books/${book.id}`} />}
          >
            Details
            <ArrowUpRight className="size-3.5 opacity-60" />
          </Button>
          <Button
            size="sm"
            className="h-9 flex-1"
            disabled={rentDisabled}
            onClick={onRent}
          >
            Rent
          </Button>
        </div>
      </div>
    </article>
  );
}
