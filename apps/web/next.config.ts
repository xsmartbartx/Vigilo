import path from "node:path";
import type { NextConfig } from "next";

// Where the company and platform pages live. Vigilo is a product with its own site; the
// catalogue of all products and the other products' pages are on the Nexora site.
const NEXORA = (process.env.NEXT_PUBLIC_NEXORA_URL ?? "https://onenexora.com").replace(/\/$/, "");

// Clerk's frontend API host is encoded in the publishable key (pk_live_<base64 of "host$">), so the
// policy follows whichever Clerk instance this deployment uses instead of hard-coding one.
function clerkHost(): string | null {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
  const encoded = key.split("_").slice(2).join("_");
  if (!encoded) return null;
  try {
    const host = Buffer.from(encoded, "base64").toString("utf8").replace(/\$$/, "");
    return /^[a-z0-9.-]+$/i.test(host) ? host : null;
  } catch {
    return null;
  }
}

function apiOrigin(): string | null {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL ?? "").origin;
  } catch {
    return null;
  }
}

// What the pages are allowed to load. 'unsafe-inline' scripts and styles are needed by Next's own
// inline bootstrap and Clerk's widget until nonces are wired in; everything else is closed.
function contentSecurityPolicy(): string {
  const clerk = clerkHost();
  const clerkOrigin = clerk ? [`https://${clerk}`] : [];
  const api = apiOrigin();
  return [
    "default-src 'self'",
    ["script-src 'self' 'unsafe-inline'", ...clerkOrigin, "https://challenges.cloudflare.com"].join(" "),
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://img.clerk.com",
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

const CSP_HEADER = "Content-Security-Policy-Report-Only";

const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  // Report-only first: it logs violations in the browser console without blocking anything, so the
  // policy can be checked against the real sign-in flow before it is enforced (then this key
  // becomes "Content-Security-Policy"). Production only: the dev server needs `eval`.
  ...(process.env.NODE_ENV === "production"
    ? [{ key: CSP_HEADER, value: contentSecurityPolicy() }]
    : []),
];

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Do not advertise the framework in an `X-Powered-By` header.
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // Dev only: the browser tests (and anyone opening http://127.0.0.1:3000)
  // use 127.0.0.1, which Next treats as a cross-origin to "localhost" and
  // blocks, taking the HMR socket and hydration with it.
  allowedDevOrigins: ["127.0.0.1"],
  // lib/brand.ts reads ../../../brand.config.json (the repo-wide source of
  // truth) — widen Turbopack's root beyond apps/web so that resolves.
  turbopack: {
    root: path.join(__dirname, "..", ".."),
  },
  // Self-hosting (Phase 9, docs/self-hosting.md): a standalone build only
  // copies the files `next build` actually traces as needed, small enough
  // to run without `node_modules` in the final image (Next's documented
  // Docker deployment mode). The trace itself needs the same monorepo-root
  // widening as Turbopack above, for the same brand.config.json reason —
  // Next's default tracing root is apps/web itself, which wouldn't see two
  // directories up.
  async redirects() {
    return [
      // Vigilo's page is now the home page of this site.
      { source: "/products/vigilo", destination: "/", permanent: true },
      // Temporary (307): the target is another site we do not control the paths of.
      { source: "/products", destination: `${NEXORA}/products`, permanent: false },
      { source: "/products/:slug", destination: `${NEXORA}/products/:slug`, permanent: false },
    ];
  },
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "..", ".."),
};

export default nextConfig;
