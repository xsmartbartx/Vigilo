// Next.js 16 renamed `middleware.ts` to `proxy.ts` (the exported function
// name changed too, but Clerk's `clerkMiddleware()` just returns a plain
// (request) => Response handler regardless of what it's re-exported as).
import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { contentSecurityPolicy, newNonce } from "./lib/csp";

export default clerkMiddleware((_auth, request) => {
  // Production only: the dev server needs `eval`, and a nonce only matters where it is served.
  if (process.env.NODE_ENV !== "production") return NextResponse.next();

  // The nonce goes on the request too: Next reads it from the request's CSP header to tag its own
  // inline scripts, and ClerkProvider (dynamic) reads `x-nonce` to tag Clerk's.
  const nonce = newNonce();
  const policy = contentSecurityPolicy(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", policy);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", policy);
  return response;
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
