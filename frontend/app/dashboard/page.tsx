"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Dashboard } from "@/lib/types";
import { Button } from "@/components/ui/button";

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

  if (!data) return <p className="p-6">{msg || "Loading…"}</p>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-semibold">{data.full_name}</h1>
      <p>{data.capacity_message}</p>
      {msg && <p className="text-sm">{msg}</p>}
      <section>
        <h2 className="font-medium mb-2">Current</h2>
        {data.current.map((r) => (
          <div key={r.id} className="border rounded p-3 mb-2">
            <p>{r.book_title}</p>
            <p className="text-sm">
              Due {r.due_at.slice(0, 10)} · {r.status}
              {r.days_remaining != null ? ` · ${r.days_remaining} days left` : ""}
              {r.days_overdue ? ` · ${r.days_overdue} days overdue` : ""}
            </p>
            <Button size="sm" onClick={() => ret(r.id)}>
              Return
            </Button>
          </div>
        ))}
      </section>
      <section>
        <h2 className="font-medium mb-2">History</h2>
        {data.history.map((r) => (
          <p key={r.id} className="text-sm">
            {r.book_title} · {r.status}
          </p>
        ))}
      </section>
    </div>
  );
}