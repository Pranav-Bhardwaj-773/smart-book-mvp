"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      setData(await api.dashboard());
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Please sign in");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function ret(id: number) {
    try {
      await api.returnBook(id);
      setMsg("Book returned successfully.");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Return failed");
    }
  }

  if (!data) {
    return (
      <p className="mx-auto max-w-2xl px-4 py-8 text-sm text-muted-foreground">
        {msg || "Loading…"}
      </p>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 px-4 py-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">{data.full_name}</h1>
        <p className="text-sm text-muted-foreground">{data.capacity_message}</p>
      </div>
      {msg && (
        <p className="text-sm text-muted-foreground" role="status">
          {msg}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-medium">Current</h2>
        {data.current.length === 0 && (
          <p className="rounded-xl border px-4 py-6 text-sm text-muted-foreground">
            You have no active rentals.
          </p>
        )}
        {data.current.map((r) => (
          <Card key={r.id} className="gap-0 py-0">
            <div className="space-y-2 p-4">
              <p className="font-medium leading-snug">{r.book_title}</p>
              <p className="text-sm text-muted-foreground">{r.authors}</p>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="outline">{r.status}</Badge>
                <Badge variant="outline">Due {r.due_at.slice(0, 10)}</Badge>
              </div>
            </div>
            <div className="flex items-center justify-between gap-2 border-t px-4 py-3">
              <p className="text-xs text-muted-foreground">
                {r.days_remaining != null ? `${r.days_remaining} days left` : ""}
                {r.days_overdue ? `${r.days_overdue} days overdue` : ""}
              </p>
              <Button size="sm" variant="outline" onClick={() => ret(r.id)}>
                Return
              </Button>
            </div>
          </Card>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">History</h2>
        <Card className="gap-0 py-0">
          {data.history.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground">No past rentals.</p>
          ) : (
            <ul>
              {data.history.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between gap-3 border-b px-4 py-3 last:border-0"
                >
                  <span className="min-w-0 truncate text-sm">{r.book_title}</span>
                  <Badge variant="outline">{r.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </div>
  );
}
