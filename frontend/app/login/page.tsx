"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Suspense } from "react";
import { useAuth } from "@/components/auth-provider";

function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const next = useSearchParams().get("next") || "/dashboard";
  const [email, setEmail] = useState("reader@smartbook.local");
  const [password, setPassword] = useState("Reader123!");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      const { access_token } = await api.login({ email, password });
      await login(access_token);
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <form onSubmit={onSubmit} className="max-w-sm mx-auto p-6 space-y-3">
      <h1 className="text-xl font-semibold">Sign in</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Input value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Button type="submit" className="w-full">
        Sign in
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
