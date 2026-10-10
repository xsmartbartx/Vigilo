import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";
import { api, ApiError } from "../../lib/api";
import type { MonitorResponse, ScoreHistoryEntry } from "../../lib/types";

const JWT_TEMPLATE = process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE ?? "vigilo-api";

function latest(scores: ScoreHistoryEntry[]) { return scores[0] ?? null; }
function tone(score: number | null) {
  if (score === null) return "text-black/45 dark:text-white/45";
  if (score >= 90) return "text-severity-pass";
  if (score >= 70) return "text-severity-medium";
  if (score >= 50) return "text-severity-high";
  return "text-severity-critical";
}
async function monitor(targetId: string, token: string): Promise<MonitorResponse | null> {
  try { return await api.getTargetMonitor(targetId, token); }
  catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e; }
}

export default async function DashboardOverviewPage() {
  const { getToken } = await auth();
  const token = await getToken({ template: JWT_TEMPLATE });
  if (!token) redirect("/sign-in");

  const [account, targets] = await Promise.all([api.getMe(token), api.listTargets(token)]);
  const data = await Promise.all(targets.map(async target => {
    const [scores, mon, alerts] = await Promise.all([
      api.getTargetScoreHistory(target.target_id, token),
      monitor(target.target_id, token),
      api.getTargetAlerts(target.target_id, token),
    ]);
    return { target, scores, mon, alerts };
  }));

  const scored = data.map(x => latest(x.scores)).filter((x): x is ScoreHistoryEntry => x !== null);
  const average = scored.length ? Math.round(scored.reduce((s, x) => s + x.score, 0) / scored.length) : null;
  const verified = targets.filter(x => x.verification_status === "active").length;
  const monitored = data.filter(x => x.mon?.enabled).length;
  const alerts = data.flatMap(x => x.alerts.map(alert => ({ target: x.target, alert })))
    .sort((a, b) => Date.parse(b.alert.created_at) - Date.parse(a.alert.created_at));
  const weakest = [...data].filter(x => latest(x.scores)).sort((a,b) => (latest(a.scores)?.score ?? 101) - (latest(b.scores)?.score ?? 101))[0];
  const limit = account.entitlements.targets_limit;
  const usage = limit === null ? 0 : Math.min(100, Math.round((targets.length / limit) * 100));

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-black/10 dark:border-white/10 p-6 md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm text-black/50 dark:text-white/50">Security workspace</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">Customer Dashboard</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-black/60 dark:text-white/60">
              Security posture, ownership, monitoring and alert signals for your applications.
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard/targets" className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white">Add target</Link>
            <Link href="/dashboard/billing" className="rounded-lg border border-black/10 dark:border-white/15 px-4 py-2 text-sm font-semibold">
              {account.entitlements.plan_id.toUpperCase()} plan
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Security score", average === null ? "—" : String(average), "portfolio average", tone(average)],
          ["Targets", String(targets.length), limit === null ? "unlimited" : `${targets.length} / ${limit}`, "text-foreground"],
          ["Verified", String(verified), verified === targets.length ? "all verified" : `${targets.length - verified} need verification`, verified === targets.length ? "text-severity-pass" : "text-severity-medium"],
          ["Monitoring", String(monitored), "active monitors", monitored ? "text-severity-pass" : "text-black/45 dark:text-white/45"],
          ["Alerts", String(alerts.length), alerts.length ? "recent signals" : "no recent alerts", alerts.length ? "text-severity-high" : "text-severity-pass"],
        ].map(([label, value, sub, color]) => (
          <div key={label} className="rounded-xl border border-black/10 dark:border-white/10 p-4">
            <p className="text-xs uppercase tracking-wide text-black/45 dark:text-white/45">{label}</p>
            <p className={`mt-3 text-2xl font-semibold ${color}`}>{value}</p>
            <p className="mt-1 text-xs text-black/50 dark:text-white/50">{sub}</p>
          </div>
        ))}
      </section>

      {!targets.length ? (
        <section className="rounded-2xl border border-dashed border-black/15 dark:border-white/15 p-10 text-center">
          <h2 className="text-lg font-semibold">Your security workspace is empty.</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-black/60 dark:text-white/60">
            Add an application to start scanning, verify ownership and enable monitoring.
          </p>
          <Link href="/dashboard/targets" className="mt-5 inline-flex rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white">
            Add your first target
          </Link>
        </section>
      ) : (
        <>
          <section className="grid gap-6 xl:grid-cols-[1.8fr_1fr]">
            <div className="rounded-2xl border border-black/10 dark:border-white/10 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">Target health</h2>
                  <p className="mt-1 text-sm text-black/50 dark:text-white/50">Current posture of every tracked application.</p>
                </div>
                <Link href="/dashboard/targets" className="text-xs underline underline-offset-2">Manage</Link>
              </div>
              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead><tr className="border-b border-black/10 dark:border-white/10 text-xs uppercase text-black/45 dark:text-white/45">
                    <th className="pb-3 pr-4">Target</th><th className="pb-3 pr-4">Score</th><th className="pb-3 pr-4">Verification</th><th className="pb-3 pr-4">Monitor</th><th className="pb-3">Action</th>
                  </tr></thead>
                  <tbody>
                    {data.map(({ target, scores, mon, alerts }) => {
                      const score = latest(scores);
                      const attention = target.verification_status !== "active" || !score || score.score < 70 || alerts.length > 0;
                      return <tr key={target.target_id} className="border-b last:border-0 border-black/10 dark:border-white/10">
                        <td className="py-4 pr-4"><p className="max-w-[280px] truncate font-medium">{target.origin}</p><p className="mt-1 text-xs text-black/45 dark:text-white/45">{attention ? "Needs attention" : "Healthy posture"}</p></td>
                        <td className={`py-4 pr-4 font-semibold ${tone(score?.score ?? null)}`}>{score?.score ?? "—"}</td>
                        <td className="py-4 pr-4 text-xs">{target.verification_status === "active" ? <span className="text-severity-pass">Verified</span> : <span className="text-severity-medium">Unverified</span>}</td>
                        <td className="py-4 pr-4 text-xs text-black/60 dark:text-white/60">{mon?.enabled ? "Active" : "Off"}</td>
                        <td className="py-4"><Link href={`/targets/${target.target_id}/monitoring`} className="text-xs underline underline-offset-2">View</Link></td>
                      </tr>;
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-6">
              <div className="rounded-2xl border border-black/10 dark:border-white/10 p-5">
                <h2 className="font-semibold">Priority queue</h2>
                <p className="mt-1 text-sm text-black/50 dark:text-white/50">Actions with the highest operational value.</p>
                <div className="mt-4 space-y-3">
                  {weakest && <Link href={`/targets/${weakest.target.target_id}/monitoring`} className="block rounded-xl border border-black/10 dark:border-white/10 p-3">
                    <p className="text-xs text-black/45 dark:text-white/45">Lowest score</p>
                    <p className="mt-1 truncate text-sm font-medium">{weakest.target.origin}</p>
                    <p className={`mt-1 text-sm font-semibold ${tone(latest(weakest.scores)?.score ?? null)}`}>Score {latest(weakest.scores)?.score ?? "—"}</p>
                  </Link>}
                  {targets.length > verified && <Link href="/dashboard/targets" className="block rounded-xl border border-black/10 dark:border-white/10 p-3">
                    <p className="text-xs text-black/45 dark:text-white/45">Ownership</p>
                    <p className="mt-1 text-sm font-medium">{targets.length - verified} target{targets.length - verified === 1 ? "" : "s"} need verification.</p>
                  </Link>}
                  {account.entitlements.monitoring_frequency && monitored < targets.length && <Link href="/dashboard/targets" className="block rounded-xl border border-black/10 dark:border-white/10 p-3">
                    <p className="text-xs text-black/45 dark:text-white/45">Monitoring</p>
                    <p className="mt-1 text-sm font-medium">{targets.length - monitored} target{targets.length - monitored === 1 ? "" : "s"} are not monitored.</p>
                  </Link>}
                  {alerts[0] && <Link href={`/targets/${alerts[0].target.target_id}/monitoring`} className="block rounded-xl border border-black/10 dark:border-white/10 p-3">
                    <p className="text-xs text-black/45 dark:text-white/45">Latest signal</p>
                    <p className="mt-1 text-sm font-medium">{alerts[0].alert.type.replaceAll("_", " ")}</p>
                    <p className="mt-1 truncate text-xs text-black/50 dark:text-white/50">{alerts[0].target.origin}</p>
                  </Link>}
                </div>
              </div>

              <div className="rounded-2xl border border-black/10 dark:border-white/10 p-5">
                <div className="flex items-center justify-between"><div><h2 className="font-semibold">Plan capacity</h2><p className="mt-1 text-sm text-black/50 dark:text-white/50">Target usage against entitlement.</p></div><Link href="/dashboard/billing" className="text-xs underline underline-offset-2">Billing</Link></div>
                <div className="mt-5"><div className="flex justify-between text-xs"><span>Targets</span><span className="text-black/50 dark:text-white/50">{limit === null ? `${targets.length} / unlimited` : `${targets.length} / ${limit}`}</span></div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/5 dark:bg-white/10"><div className="h-full rounded-full bg-brand-accent" style={{width: `${limit === null ? 16 : usage}%`}} /></div>
                </div>
                <div className="mt-4 rounded-xl bg-black/[0.03] dark:bg-white/[0.04] p-3 text-xs text-black/60 dark:text-white/60">
                  Monitoring: {account.entitlements.monitoring_frequency ?? "not included"} · Active scanning: {account.entitlements.active_tier_allowed ? "enabled" : "not included"}
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-black/10 dark:border-white/10 p-5">
              <div className="flex items-center justify-between"><div><h2 className="font-semibold">Recent alerts</h2><p className="mt-1 text-sm text-black/50 dark:text-white/50">Latest signals across the estate.</p></div><span className="text-xs text-black/45 dark:text-white/45">{alerts.length} total</span></div>
              <div className="mt-4 space-y-3">
                {!alerts.length ? <p className="text-sm text-black/50 dark:text-white/50">No alert activity yet.</p> : alerts.slice(0, 6).map(({target, alert}) =>
                  <Link key={alert.alert_id} href={`/targets/${target.target_id}/monitoring`} className="flex items-start justify-between gap-4 rounded-xl border border-black/10 dark:border-white/10 p-3">
                    <div className="min-w-0"><p className="text-sm font-medium">{alert.type.replaceAll("_", " ")}</p><p className="mt-1 truncate text-xs text-black/50 dark:text-white/50">{target.origin}</p></div>
                    <span className="shrink-0 text-xs text-black/45 dark:text-white/45">{new Date(alert.created_at).toLocaleDateString()}</span>
                  </Link>
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-black/10 dark:border-white/10 p-5">
              <h2 className="font-semibold">Recommended next steps</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Link href="/dashboard/targets" className="rounded-xl border border-black/10 dark:border-white/10 p-4"><p className="text-sm font-semibold">Add and verify targets</p><p className="mt-1 text-xs text-black/50 dark:text-white/50">Unlock the active-tier scan path.</p></Link>
                <Link href="/dashboard/api-keys" className="rounded-xl border border-black/10 dark:border-white/10 p-4"><p className="text-sm font-semibold">Connect CI / MCP</p><p className="mt-1 text-xs text-black/50 dark:text-white/50">Manage keys for automated workflows.</p></Link>
                <Link href="/dashboard/billing" className="rounded-xl border border-black/10 dark:border-white/10 p-4"><p className="text-sm font-semibold">Review capacity</p><p className="mt-1 text-xs text-black/50 dark:text-white/50">Increase limits as the estate grows.</p></Link>
                <Link href="/dashboard/branding" className="rounded-xl border border-black/10 dark:border-white/10 p-4"><p className="text-sm font-semibold">Configure reports</p><p className="mt-1 text-xs text-black/50 dark:text-white/50">Manage white-label reporting.</p></Link>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
