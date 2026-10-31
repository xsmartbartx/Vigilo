// Clerk's frontend API host is encoded in the publishable key (pk_live_<base64 of "host$">), so the
// policy follows whichever Clerk instance this deployment uses instead of hard-coding one.
function clerkHost(): string | null {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
  const encoded = key.split("_").slice(2).join("_");
  if (!encoded) return null;
  try {
    const host = atob(encoded).replace(/\$$/, "");
    return /^[a-z0-9.-]+$/i.test(host) ? host : null;
  } catch {
    return null;
  }
}

// The browser calls the API directly (lib/api.ts), so its origin must be allowed in connect-src.
// Same variable and default as lib/api.ts.
function apiOrigin(): string | null {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").origin;
  } catch {
    return null;
  }
}

// A fresh, unguessable value for every request.
export function newNonce(): string {
  return btoa(crypto.randomUUID());
}

// What the pages are allowed to load. Scripts need the per-request nonce ('strict-dynamic' then lets
// those scripts load the ones they depend on, such as Clerk's), so there is no 'unsafe-inline' for
// scripts. Styles keep 'unsafe-inline': Clerk's widget injects style tags and a style cannot run code.
export function contentSecurityPolicy(nonce: string): string {
  const clerk = clerkHost();
  const clerkOrigin = clerk ? [`https://${clerk}`] : [];
  const api = apiOrigin();
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    // The API origin serves the score badge image (components/monitoring/BadgeEmbed.tsx).
    ["img-src 'self' data: blob: https://img.clerk.com", ...(api ? [api] : [])].join(" "),
    "font-src 'self' data:",
    ["connect-src 'self'", ...clerkOrigin, ...(api ? [api] : [])].join(" "),
    "frame-src https://challenges.cloudflare.com",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}
