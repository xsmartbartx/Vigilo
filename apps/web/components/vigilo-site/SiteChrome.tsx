import type { ReactNode } from "react";
import Link from "next/link";
import { Show, UserButton } from "@clerk/nextjs";
import { brand } from "../../lib/brand";
import { NEXORA_URL } from "../../lib/site";
import { Footer } from "../Footer";

const NAV = [
  { href: "/#how", label: "How it works" },
  { href: "/#features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
  { href: "/#faq", label: "FAQ" },
] as const;

const BUTTON =
  "inline-flex h-9 items-center rounded-nx-md bg-nx-accent px-4 text-sm font-semibold text-nx-on-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent";

// Two bars, as on a product site under a company site: a thin company bar with the way
// back to NEXORA, then the product bar with this product's own navigation.
export function SiteHeader() {
  return (
    <header className="sticky -top-9 z-30">
      <div className="border-b border-nx-border bg-nx-surface">
        <div className="mx-auto flex h-9 w-full max-w-[1120px] items-center justify-between px-4 text-xs sm:px-6">
          <a href={NEXORA_URL} className="font-semibold tracking-[0.12em] text-nx-text hover:underline">
            NEXORA
          </a>
          <a href={`${NEXORA_URL}/products`} className="text-nx-text-muted hover:text-nx-text hover:underline">
            All products
          </a>
        </div>
      </div>
      <div className="border-b border-nx-border bg-nx-bg/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-[1120px] items-center gap-x-6 px-4 sm:px-6">
          <Link href="/" className="text-lg font-semibold text-nx-text">
            {brand.name}
          </Link>
          <nav aria-label={`${brand.name} sections`} className="flex min-w-0 flex-1 gap-x-5 overflow-x-auto text-sm [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="whitespace-nowrap text-nx-text-muted hover:text-nx-text hover:underline"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-x-4 text-sm">
            <Show when="signed-out">
              <Link href="/sign-in" className="hidden text-nx-text-muted hover:text-nx-text hover:underline sm:inline">
                Sign in
              </Link>
              <Link href="/#scan" className={BUTTON}>
                Scan free
              </Link>
            </Show>
            <Show when="signed-in">
              <Link href="/dashboard" className="text-nx-text-muted hover:text-nx-text hover:underline">
                Dashboard
              </Link>
              <UserButton />
            </Show>
          </div>
        </div>
      </div>
    </header>
  );
}

export function SiteShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <>
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <Footer />
    </>
  );
}
