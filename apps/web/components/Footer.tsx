import Link from "next/link";
import { brand } from "../lib/brand";
import { NEXORA_URL } from "../lib/site";

export function Footer({ name }: { name?: string } = {}) {
  return (
    <footer className="mt-auto border-t border-black/10 dark:border-white/10 px-6 py-6 text-sm text-black/60 dark:text-white/60">
      <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        <Link href="/trust" className="hover:underline">
          Trust and security
        </Link>
        <Link href="/privacy" className="hover:underline">
          Privacy Policy
        </Link>
        <Link href="/terms" className="hover:underline">
          Terms of Service
        </Link>
        <Link href="/cookies" className="hover:underline">
          Cookie Policy
        </Link>
        <Link href="/aup" className="hover:underline">
          Acceptable Use Policy
        </Link>
        <a href={`mailto:${brand.supportEmail}`} className="hover:underline">
          Contact
        </a>
      </nav>
      <p className="mt-4 text-center text-xs text-black/60 dark:text-white/65">
        &copy; {new Date().getFullYear()} {name ?? brand.legalName}
        {" · "}
        <a href={NEXORA_URL} className="hover:underline">
          A NEXORA product
        </a>
      </p>
    </footer>
  );
}
