import { Spinner } from "@/components/ui/spinner";

export default function Loading() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16"
      role="status"
      aria-live="polite"
    >
      <Spinner className="size-8" />
      <p className="text-sm text-muted-foreground">Loading…</p>
    </div>
  );
}