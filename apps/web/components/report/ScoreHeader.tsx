import type { ScanReportResponse } from "../../lib/types";
import { formatUtcDateTime } from "../../lib/datetime";

const GRADE_COLOR: Record<string, string> = {
  A: "text-severity-pass",
  B: "text-severity-pass",
  C: "text-severity-medium",
  D: "text-severity-high",
  F: "text-severity-critical",
};

export function ScoreHeader({ report }: { report: ScanReportResponse }) {
  const gradeColor = GRADE_COLOR[report.grade] ?? "text-severity-critical";
  const branding = report.branding;

  return (
    <div
      className="border-b border-black/10 dark:border-white/10 pb-6 mb-6"
      style={
        branding?.primary_color
          ? { borderBottomColor: branding.primary_color, borderBottomWidth: 3 }
          : undefined
      }
    >
      {branding?.logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- arbitrary, account-supplied URL
        <img src={branding.logo_url} alt="" className="h-8 mb-3" />
      ) : null}
      <p className="text-sm text-black/60 dark:text-white/60 break-all">{report.target_origin}</p>
      <div className="flex items-baseline gap-4 mt-1">
        <span className={`text-5xl font-bold ${gradeColor}`}>{report.grade}</span>
        <span className="text-2xl">{report.score.toFixed(0)} / 100</span>
      </div>
      {report.stack && report.stack.length > 0 ? (
        <p className="mt-2 text-sm text-black/70 dark:text-white/70">
          <span className="font-medium">Detected: </span>
          {report.stack.join(" · ")}
        </p>
      ) : null}
      <p className="text-xs text-black/60 dark:text-white/65 mt-2">
        Scanned {formatUtcDateTime(report.generated_at)} · registry {report.registry_version}
      </p>
      <p className="text-xs text-black/60 dark:text-white/65 mt-4 max-w-prose">
        This is an automated assessment, not a certification, and reflects the target&apos;s state
        at the scan timestamp under the registry version above.
      </p>
      {branding?.footer_text ? (
        <p className="text-xs text-black/60 dark:text-white/65 mt-2">{branding.footer_text}</p>
      ) : null}
    </div>
  );
}
