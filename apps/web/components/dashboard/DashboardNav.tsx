"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/targets", label: "Targets" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/dashboard/api-keys", label: "API keys" },
  { href: "/dashboard/branding", label: "Branding" },
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <>
      {LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
              active
                ? "bg-black/[0.06] text-foreground dark:bg-white/[0.08]"
                : "text-black/60 hover:bg-black/[0.03] hover:text-foreground dark:text-white/60 dark:hover:bg-white/[0.04] dark:hover:text-foreground"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </>
  );
}
