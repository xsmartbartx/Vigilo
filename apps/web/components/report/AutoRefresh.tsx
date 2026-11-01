"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// Re-reads the page on a timer while a report is still being built, so the
// visitor does not have to refresh by hand. Stops after `maxSeconds` and then
// says so, because the page would otherwise keep promising it updates by itself.
export function AutoRefresh({ everySeconds = 3, maxSeconds = 300 }: { everySeconds?: number; maxSeconds?: number }) {
  const router = useRouter();
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => {
      if (Date.now() - started > maxSeconds * 1000) {
        clearInterval(id);
        setTimedOut(true);
        return;
      }
      router.refresh();
    }, everySeconds * 1000);
    return () => clearInterval(id);
  }, [router, everySeconds, maxSeconds]);
  if (!timedOut) return null;
  return (
    <p role="status" className="mt-4 text-sm text-black/70 dark:text-white/70">
      This is taking longer than usual. Reload the page in a minute, or start a new scan from the
      home page.
    </p>
  );
}
