"use client";

import { useState } from "react";

export function AgentPromptBlock({
  prompt,
  printMode = false,
}: {
  prompt: string;
  printMode?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be denied by the browser — the prompt text is
      // still fully visible and selectable, so this fails soft.
    }
  }

  return (
    <div className="mt-3 rounded-md border border-brand-accent/40 bg-brand-accent/10 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-nx-on-accent-soft">
          Paste into your AI coding tool
        </p>
        {!printMode ? (
          <button
            type="button"
            onClick={handleCopy}
            className="shrink-0 min-h-8 rounded border border-brand-accent/40 px-3 text-xs font-medium text-nx-on-accent-soft"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </div>
      <p className="mt-1.5 whitespace-pre-wrap text-sm [overflow-wrap:anywhere]">{prompt}</p>
    </div>
  );
}
