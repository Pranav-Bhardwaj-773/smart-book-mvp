"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { BookAvatar } from "@/components/book-avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardTitle,
} from "@/components/ui/card";
import type { Book } from "@/lib/types";

function availabilityBadge(book: Book) {
  if (book.status === "archived") {
    return { label: "Archived", variant: "secondary" as const };
  }
  if (book.available_copies <= 0) {
    return { label: "Out of stock", variant: "destructive" as const };
  }
  if (book.available_copies < book.total_copies) {
    return {
      label: `${book.available_copies} left`,
      variant: "outline" as const,
    };
  }
  return { label: "Available", variant: "default" as const };
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
  const status = availabilityBadge(book);

  return (
    <Card className="relative h-full overflow-hidden transition-shadow duration-300 hover:shadow-md">
      <Badge
        variant={status.variant}
        className="pointer-events-none absolute right-2 top-2 z-50 uppercase shadow-md ring-2 ring-background"
      >
        {status.label}
      </Badge>
      <div className="mx-auto w-[60%] max-w-[8rem] pb-3 pt-8">
        <Link href={`/books/${book.id}`} className="relative z-0 block w-full">
          <BookAvatar
            title={book.title}
            coverUrl={book.cover_url}
            variant="cover"
            className="relative z-0 aspect-[2/3] h-auto w-full rounded-lg object-cover ring-0"
          />
        </Link>
      </div>

      <CardContent className="flex flex-1 flex-col gap-3 pt-2">
        <div className="space-y-1">
          <CardTitle className="line-clamp-2 text-base">
            <Link
              href={`/books/${book.id}`}
              className="hover:text-primary hover:underline hover:underline-offset-2"
            >
              {book.title}
            </Link>
          </CardTitle>
          <CardDescription className="line-clamp-1">
            {book.authors}
          </CardDescription>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {book.category ? (
            <Badge variant="secondary">{book.category}</Badge>
          ) : null}
          <Badge variant="outline">{book.publication_year}</Badge>
        </div>
      </CardContent>

      <CardFooter className="gap-2 border-t-0 bg-transparent pt-0">
        <Button
          size="sm"
          variant="outline"
          className="flex-1 justify-between"
          nativeButton={false}
          render={<Link href={`/books/${book.id}`} />}
        >
          Details
          <ArrowUpRight className="size-3.5 opacity-70" />
        </Button>
        <Button
          size="sm"
          className="flex-1"
          disabled={rentDisabled}
          onClick={onRent}
        >
          Rent
        </Button>
      </CardFooter>
    </Card>
  );
}
