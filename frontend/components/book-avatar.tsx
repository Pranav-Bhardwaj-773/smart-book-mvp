"use client";

import { useState } from "react";
import { cn } from "cn";

export function BookAvatar({
  title,
  coverUrl,
  className,
}: {
  title: string;
  coverUrl: string | null;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const initials = title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");

  if (!coverUrl || failed) {
    return (
      <div
        aria-hidden
        className={cn(
          "flex size-14 shrink-0 items-center justify-center rounded-full border bg-muted text-sm font-medium text-muted-foreground",
          className
        )}
      >
        {initials || "BK"}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={coverUrl}
      alt=""
      onError={() => setFailed(true)}
      className={cn("size-14 shrink-0 rounded-full border object-cover", className)}
    />
  );
}
