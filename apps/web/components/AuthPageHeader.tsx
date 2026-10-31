import Link from "next/link";
import { brand } from "../lib/brand";

// Sign-in and sign-up are the bare Clerk card: say whose it is, and give a way back to the site.
export function AuthPageHeader() {
  return (
    <header className="flex flex-col items-center gap-1 text-center">
      <Link href="/" className="text-xl font-semibold">
        {brand.name}
      </Link>
      <Link href="/" className="text-xs text-black/60 underline underline-offset-2 dark:text-white/60">
        &larr; Back to {brand.name}
      </Link>
    </header>
  );
}
