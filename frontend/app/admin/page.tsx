"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import type { Book, User } from "@/lib/types";

type AdminStats = {
  books: number;
  users: number;
  active_rentals: number;
  overdue_rentals: number;
};

type AdminRental = {
  id: number;
  book_id: number;
  book_title: string;
  authors: string;
  status: string;
  due_at: string;
  user_id: number;
  user_email: string;
  user_name: string;
};

type Tab = "books" | "users" | "rentals";

export default function AdminPage() {
  const { user, ready } = useAuth();
  const [tab, setTab] = useState<Tab>("books");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [rentals, setRentals] = useState<AdminRental[]>([]);
  const [rentalStatus, setRentalStatus] = useState("");
  const [msg, setMsg] = useState("");
  const [newBook, setNewBook] = useState({
    isbn: "",
    title: "",
    authors: "",
    description: "",
    total_copies: 1,
  });

  async function reload() {
    setMsg("");
    try {
      const [s, b, u, r] = await Promise.all([
        api.adminStats() as Promise<AdminStats>,
        api.adminBooks(),
        api.adminUsers(),
        api.adminRentals(rentalStatus) as Promise<AdminRental[]>,
      ]);
      setStats(s);
      setBooks(b);
      setUsers(u);
      setRentals(r);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed to load admin data");
    }
  }

  useEffect(() => {
    if (!ready || user?.role !== "admin") return;
    let cancelled = false;
    setMsg("");
    Promise.all([
      api.adminStats() as Promise<AdminStats>,
      api.adminBooks(),
      api.adminUsers(),
      api.adminRentals(rentalStatus) as Promise<AdminRental[]>,
    ])
      .then(([s, b, u, r]) => {
        if (cancelled) return;
        setStats(s);
        setBooks(b);
        setUsers(u);
        setRentals(r);
      })
      .catch((e) => {
        if (cancelled) return;
        setMsg(e instanceof Error ? e.message : "Failed to load admin data");
      });
    return () => {
      cancelled = true;
    };
  }, [ready, user, rentalStatus]);

  async function run(fn: () => Promise<unknown>) {
    try {
      await fn();
      await reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (!ready) {
    return (
      <p className="mx-auto max-w-5xl px-4 py-8 text-sm text-muted-foreground">
        Loading…
      </p>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="mx-auto max-w-5xl space-y-2 px-4 py-8">
        <p>Admin only. Sign in as admin@smartbook.local</p>
        <Link href="/login" className="text-sm underline underline-offset-4">
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4 px-4 py-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Administrator</h1>
        <p className="text-sm text-muted-foreground">
          Books, members, and rentals.
        </p>
      </div>
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(
            [
              ["Books", stats.books],
              ["Users", stats.users],
              ["Active", stats.active_rentals],
              ["Overdue", stats.overdue_rentals],
            ] as const
          ).map(([label, value]) => (
            <Card key={label} size="sm" className="py-0">
              <CardContent className="p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-lg font-medium">{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {msg && (
        <p className="text-sm text-destructive" role="alert">
          {msg}
        </p>
      )}

      <div className="flex gap-2">
        <Button
          variant={tab === "books" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("books")}
        >
          Books
        </Button>
        <Button
          variant={tab === "users" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("users")}
        >
          Users
        </Button>
        <Button
          variant={tab === "rentals" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("rentals")}
        >
          Rentals
        </Button>
      </div>

      {tab === "books" && (
        <div className="space-y-4">
          <form
            className="grid gap-2 rounded-xl border p-3 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              run(() =>
                api.adminAddBook({
                  ...newBook,
                  summary: newBook.description,
                  total_copies: Number(newBook.total_copies),
                }),
              );
            }}
          >
            <Input
              placeholder="ISBN"
              value={newBook.isbn}
              onChange={(e) => setNewBook({ ...newBook, isbn: e.target.value })}
              required
            />
            <Input
              placeholder="Title"
              value={newBook.title}
              onChange={(e) =>
                setNewBook({ ...newBook, title: e.target.value })
              }
              required
            />
            <Input
              placeholder="Authors"
              value={newBook.authors}
              onChange={(e) =>
                setNewBook({ ...newBook, authors: e.target.value })
              }
              required
            />
            <Input
              placeholder="Description"
              value={newBook.description}
              onChange={(e) =>
                setNewBook({ ...newBook, description: e.target.value })
              }
            />
            <Input
              type="number"
              min={1}
              value={newBook.total_copies}
              onChange={(e) =>
                setNewBook({
                  ...newBook,
                  total_copies: Number(e.target.value),
                })
              }
            />
            <Button type="submit">Add book</Button>
          </form>

          <Card className="gap-0 overflow-hidden py-0">
            <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Title</th>
                  <th className="px-4 py-2 font-medium">Copies</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {books.map((b) => (
                  <tr key={b.id} className="border-b last:border-0">
                    <td className="px-4 py-3">{b.title}</td>
                    <td className="px-4 py-3">
                      {b.available_copies}/{b.total_copies}
                    </td>
                    <td className="px-4 py-3">{b.status.replaceAll("_", " ")}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                      <Button
                        size="sm"
                        onClick={() => run(() => api.adminInventory(b.id, 1))}
                      >
                        +1
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => run(() => api.adminInventory(b.id, -1))}
                      >
                        -1
                      </Button>
                      {b.status === "archived" ? (
                        <Button
                          size="sm"
                          onClick={() => run(() => api.adminRestore(b.id))}
                        >
                          Restore
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => run(() => api.adminArchive(b.id))}
                        >
                          Archive
                        </Button>
                      )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </Card>
        </div>
      )}

      {tab === "users" && (
        <Card className="gap-0 overflow-hidden py-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Role</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-0">
                  <td className="px-4 py-3">{u.full_name}</td>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3">{u.role}</td>
                  <td className="px-4 py-3">{u.status}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                    {u.role !== "admin" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            run(() => api.adminSetStatus(u.id, "active"))
                          }
                        >
                          Activate
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() =>
                            run(() => api.adminSetStatus(u.id, "blocked"))
                          }
                        >
                          Block
                        </Button>
                      </>
                    )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </Card>
      )}

      {tab === "rentals" && (
        <div className="space-y-3">
          <NativeSelect
            value={rentalStatus}
            onChange={(e) => setRentalStatus(e.target.value)}
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="overdue">Overdue</option>
            <option value="returned">Returned</option>
          </NativeSelect>
          <Card className="gap-0 overflow-hidden py-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-4 py-2 font-medium">ID</th>
                  <th className="px-4 py-2 font-medium">User</th>
                  <th className="px-4 py-2 font-medium">Book</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Due</th>
                  <th className="px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rentals.map((r) => (
                  <tr key={r.id} className="border-b last:border-0">
                    <td className="px-4 py-3">{r.id}</td>
                    <td className="px-4 py-3">
                      {r.user_name}
                      <br />
                      <span className="text-muted-foreground">
                        {r.user_email}
                      </span>
                    </td>
                    <td className="px-4 py-3">{r.book_title}</td>
                    <td className="px-4 py-3">{r.status}</td>
                    <td className="px-4 py-3">{r.due_at.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      {(r.status === "active" || r.status === "overdue") && (
                        <Button
                          size="sm"
                          onClick={() => run(() => api.adminReturn(r.id))}
                        >
                          Return
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </Card>
        </div>
      )}
    </div>
  );
}
