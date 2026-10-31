import path from "node:path";
import type { NextConfig } from "next";

// Where the company and platform pages live. Vigilo is a product with its own site; the
// catalogue of all products and the other products' pages are on the Nexora site.
const NEXORA = (process.env.NEXT_PUBLIC_NEXORA_URL ?? "https://onenexora.com").replace(/\/$/, "");

const securityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  // The Content-Security-Policy is set per request in proxy.ts (it carries a nonce).
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
