"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
    reload();
  }, [ready, user, rentalStatus]);

  async function run(fn: () => Promise<unknown>) {
    try {
      await fn();
      await reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (!ready) return <p className="p-6">Loading…</p>;

  if (!user || user.role !== "admin") {
    return (
      <div className="p-6 space-y-2">
        <p>Admin only. Sign in as admin@smartbook.local</p>
        <Link href="/login" className="underline text-sm">
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <h1 className="text-xl font-semibold">Administrator</h1>
      {stats && (
        <p className="text-sm text-muted-foreground">
          Books {stats.books} · Users {stats.users} · Active rentals{" "}
          {stats.active_rentals} · Overdue {stats.overdue_rentals}
        </p>
      )}
      {msg && <p className="text-sm text-red-600">{msg}</p>}

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
            className="grid sm:grid-cols-2 gap-2 border rounded p-3"
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

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left border-b">
                  <th className="p-2">Title</th>
                  <th className="p-2">Copies</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {books.map((b) => (
                  <tr key={b.id} className="border-b">
                    <td className="p-2">{b.title}</td>
                    <td className="p-2">
                      {b.available_copies}/{b.total_copies}
                    </td>
                    <td className="p-2">{b.status.replaceAll("_", " ")}</td>
                    <td className="p-2 flex flex-wrap gap-1">
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "users" && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b">
                <th className="p-2">Name</th>
                <th className="p-2">Email</th>
                <th className="p-2">Role</th>
                <th className="p-2">Status</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b">
                  <td className="p-2">{u.full_name}</td>
                  <td className="p-2">{u.email}</td>
                  <td className="p-2">{u.role}</td>
                  <td className="p-2">{u.status}</td>
                  <td className="p-2 flex gap-1">
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "rentals" && (
        <div className="space-y-3">
          <select
            className="border rounded h-8 px-2 text-sm"
            value={rentalStatus}
            onChange={(e) => setRentalStatus(e.target.value)}
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="overdue">Overdue</option>
            <option value="returned">Returned</option>
          </select>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left border-b">
                  <th className="p-2">ID</th>
                  <th className="p-2">User</th>
                  <th className="p-2">Book</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Due</th>
                  <th className="p-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rentals.map((r) => (
                  <tr key={r.id} className="border-b">
                    <td className="p-2">{r.id}</td>
                    <td className="p-2">
                      {r.user_name}
                      <br />
                      <span className="text-muted-foreground">
                        {r.user_email}
                      </span>
                    </td>
                    <td className="p-2">{r.book_title}</td>
                    <td className="p-2">{r.status}</td>
                    <td className="p-2">{r.due_at.slice(0, 10)}</td>
                    <td className="p-2">
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
        </div>
      )}
    </div>
  );
}
