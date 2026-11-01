import type { ReportFindingResponse } from "../../lib/types";
import { AgentPromptBlock } from "./AgentPromptBlock";
import { EvidencePanel } from "./EvidencePanel";
import { SuppressFindingButton } from "./SuppressFindingButton";

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-fill-critical",
  high: "bg-fill-high",
  medium: "bg-fill-medium",
  low: "bg-fill-low",
  info: "bg-black/40 dark:bg-white/40",
};

const EFFORT_LABEL: Record<string, string> = {
  trivial: "Trivial fix",
  small: "~15 min",
  medium: "~1 hour",
  large: "Half a day+",
};

export function FindingCard({
  finding,
  printMode = false,
  targetId,
  onSuppressed,
}: {
  finding: ReportFindingResponse;
  printMode?: boolean;
  targetId?: string | null;
  onSuppressed?: (fingerprint: string) => void;
}) {
  return (
    <div
      id={`finding-${finding.fingerprint}`}
      className="scroll-mt-4 rounded-lg border border-black/10 dark:border-white/10 p-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <span
            className={`inline-block rounded px-2 py-0.5 text-xs font-medium text-white ${SEVERITY_BADGE[finding.severity] ?? "bg-black/40"}`}
          >
            {finding.severity}
          </span>
          <h3 className="mt-1.5 font-medium [overflow-wrap:anywhere]">{finding.title}</h3>
        </div>
        <span className="shrink-0 text-xs text-black/60 dark:text-white/65">{finding.check_id}</span>
      </div>

      <p className="mt-2 text-sm text-black/70 dark:text-white/70 [overflow-wrap:anywhere]">{finding.summary}</p>
      {finding.why_here ? (
        <p className="mt-2 text-sm [overflow-wrap:anywhere]">
          <span className="font-medium">Why this matters for your app: </span>
          {finding.why_here}
        </p>
      ) : null}

      <div className="mt-3 rounded-md bg-black/5 dark:bg-white/5 p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-black/60 dark:text-white/65">
            How to fix this
          </p>
          {finding.remediation.estimated_effort ? (
            <span className="shrink-0 rounded-full bg-black/10 dark:bg-white/10 px-2 py-0.5 text-xs">
              {EFFORT_LABEL[finding.remediation.estimated_effort] ??
                finding.remediation.estimated_effort}
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-sm [overflow-wrap:anywhere]">{finding.remediation.explanation}</p>
        <p className="mt-2 text-xs text-black/60 dark:text-white/65 [overflow-wrap:anywhere]">
          <span className="font-medium">Impact: </span>
          {finding.remediation.impact}
        </p>
        {finding.remediation.remediation_steps.length > 0 ? (
          <ol className="mt-2 list-decimal space-y-1 pl-4 text-sm [overflow-wrap:anywhere]">
            {finding.remediation.remediation_steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        ) : null}
        <AgentPromptBlock prompt={finding.remediation.agent_prompt} printMode={printMode} />
      </div>

      {finding.references.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {finding.references.map((reference) => (
            <li key={reference}>
              <a
                href={reference}
                target="_blank"
                rel="noreferrer noopener"
                className="text-brand-accent underline underline-offset-2 [overflow-wrap:anywhere]"
              >
                {reference}
              </a>
            </li>
          ))}
        </ul>
      ) : null}

      <EvidencePanel evidence={finding.evidence} defaultOpen={printMode} />

      {targetId && onSuppressed && !printMode ? (
        <div className="mt-3 border-t border-black/5 dark:border-white/10 pt-3">
          <SuppressFindingButton
            targetId={targetId}
            fingerprint={finding.fingerprint}
            checkId={finding.check_id}
            onSuppressed={() => onSuppressed(finding.fingerprint)}
          />
        </div>
      ) : null}
    </div>
  );
}
