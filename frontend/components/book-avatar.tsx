"use client";

import { useState } from "react";
import { cn } from "cn";

export function BookAvatar({
  title,
  coverUrl,
  className,
  variant = "circle",
}: {
  title: string;
  coverUrl: string | null;
  className?: string;
  variant?: "circle" | "cover";
}) {
  const [failed, setFailed] = useState(false);
  const initials = title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");

  const isCover = variant === "cover";
  const fallbackClass = isCover
    ? "flex aspect-[2/3] w-full shrink-0 items-center justify-center rounded-md bg-linear-to-br from-muted via-muted/80 to-accent text-lg font-semibold tracking-tight text-muted-foreground shadow-md ring-1 ring-foreground/10"
    : "flex size-14 shrink-0 items-center justify-center rounded-full border bg-muted text-sm font-medium text-muted-foreground";
  const imageClass = isCover
    ? "aspect-[2/3] w-full shrink-0 rounded-md object-cover shadow-md ring-1 ring-foreground/10"
    : "size-14 shrink-0 rounded-full border object-cover";

  if (!coverUrl || failed) {
    return (
      <div aria-hidden className={cn(fallbackClass, className)}>
        {initials || "BK"}
      </div>
    );
  }

  return (
    <img
      src={coverUrl}
      alt=""
      onError={() => setFailed(true)}
      className={cn(imageClass, className)}
    />
  );
}
