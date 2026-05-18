"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GlassCard } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const res = await login(username, password);
      window.localStorage.setItem("aim_token", res.access_token);
      window.localStorage.setItem("aim_user", JSON.stringify(res.user));
      router.push("/dashboard");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <GlassCard className="w-full max-w-sm">
        <h1 className="mb-6 text-center text-xl font-semibold tracking-wide">
          AI Manager
        </h1>
        <form onSubmit={submit} className="space-y-4">
          <Input
            placeholder="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
          <Input
            type="password"
            placeholder="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {err && <p className="text-xs text-red-400">{err}</p>}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </GlassCard>
    </div>
  );
}
