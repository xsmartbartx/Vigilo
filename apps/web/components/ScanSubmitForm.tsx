"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "../lib/api";

// People paste what they see in the address bar or what they remember: "example.com". Assume https
// when no scheme was typed, and say so plainly if what is left is not a web address.
export function normalizeTargetUrl(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    const url = new URL(withScheme);
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    if (!url.hostname.includes(".") && url.hostname !== "localhost") return null;
    return withScheme;
  } catch {
    return null;
  }
}

export function ScanSubmitForm() {
  const router = useRouter();
  const [targetUrl, setTargetUrl] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const normalized = normalizeTargetUrl(targetUrl);
    if (!normalized) {
      setError("Enter a website address, like example.com or https://example.com.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.submitScan({ target_url: normalized, email });
      router.push(`/reports/${result.scan_job_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4">
      <div>
        <label htmlFor="target_url" className="block text-sm font-medium mb-1">
          Site URL
        </label>
        <input
          id="target_url"
          name="url"
          type="text"
          inputMode="url"
          autoComplete="url"
          autoCapitalize="none"
          spellCheck={false}
          required
          placeholder="example.com"
          value={targetUrl}
          onChange={(event) => setTargetUrl(event.target.value)}
          className="w-full rounded-md border border-black/10 dark:border-white/20 px-3 py-2 bg-transparent"
        />
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">
          Email — your scans are saved to this address
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-md border border-black/10 dark:border-white/20 px-3 py-2 bg-transparent"
        />
      </div>
      {error ? <p className="text-severity-critical text-sm">{error}</p> : null}
      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-brand-primary text-white py-2 font-medium disabled:opacity-60"
      >
        {submitting ? "Starting scan…" : "Scan it"}
      </button>
    </form>
  );
}
