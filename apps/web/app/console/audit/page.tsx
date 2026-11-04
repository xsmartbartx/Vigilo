import Link from "next/link";
import { ApiError } from "../../../lib/api";
import { describeAudit } from "../../../lib/nexora/audit-labels";
import { getActiveOrg, loadAuditPage } from "../../../lib/nexora/data";
import { Badge, Button, Card, EmptyState } from "../../../components/ui";

export const metadata = { title: "Audit log" };

const WHEN = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ cursor?: string; action?: string }>;
}) {
  const { cursor, action } = await searchParams;
  const org = await getActiveOrg();

  if (org.role !== "owner" && org.role !== "admin") {
    return (
      <div className="space-y-4">
        <h1 className="text-[28px] font-bold leading-[34px] text-nx-text">Audit log</h1>
        <p className="text-sm text-nx-text-muted">Only owners and admins of {org.name} can read its audit log.</p>
      </div>
    );
  }

  let page;
  try {
    page = await loadAuditPage(org.id, { cursor, action });
  } catch (err) {
    // A stale or tampered cursor: start again from the newest events.
    if (err instanceof ApiError && err.status === 422) page = await loadAuditPage(org.id, { action });
    else throw err;
  }

  const filtered = Boolean(action);
  const olderHref = page.next_cursor
    ? `/console/audit?${new URLSearchParams({ ...(action ? { action } : {}), cursor: page.next_cursor })}`
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-bold leading-[34px] text-nx-text">Audit log</h1>
        <p className="mt-1 text-sm text-nx-text-muted">
          Who did what in {org.name}, newest first. Times are UTC. Entries cannot be edited or deleted.
        </p>
      </div>

      <form method="get" className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <label htmlFor="audit-action" className="text-sm font-medium text-nx-text">
            Show
          </label>
          <select
            id="audit-action"
            name="action"
            defaultValue={action ?? ""}
            className="h-10 rounded-nx-md border border-nx-border-input bg-nx-bg px-2 text-sm text-nx-text focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-nx-accent"
          >
            <option value="">Everything</option>
            {page.actions.map((a) => (
              <option key={a} value={a}>
                {a.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" variant="secondary">
          Apply
        </Button>
        {filtered ? (
          <Link href="/console/audit" className="pb-2 text-sm text-nx-link underline underline-offset-2">
            Clear filter
          </Link>
        ) : null}
      </form>

      {page.events.length === 0 ? (
        <EmptyState
          title={filtered ? "Nothing matches that filter" : "No activity yet"}
          body={
            filtered
              ? "Try a different filter, or clear it to see everything."
              : "Changes to members, keys, targets, plans and sharing will appear here as they happen."
          }
        />
      ) : (
        <Card
          tabIndex={0}
          role="region"
          aria-label="Audit log entries"
          className="relative overflow-x-auto p-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent"
        >
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Organisation audit log</caption>
            <thead className="border-b border-nx-border text-nx-text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">When (UTC)</th>
                <th scope="col" className="px-4 py-3 font-medium">Who</th>
                <th scope="col" className="px-4 py-3 font-medium">What</th>
              </tr>
            </thead>
            <tbody>
              {page.events.map((e) => (
                <tr key={e.event_id} className="border-b border-nx-border align-top last:border-0">
                  <td className="whitespace-nowrap px-4 py-3 text-nx-text-muted">
                    <time dateTime={e.occurred_at}>{WHEN.format(new Date(e.occurred_at))}</time>
                  </td>
                  <td className="break-all px-4 py-3 text-nx-text">
                    {e.actor_label}{" "}
                    {e.actor_kind === "system" ? <Badge>automatic</Badge> : null}
                  </td>
                  <td className="break-words px-4 py-3 text-nx-text">{describeAudit(e)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {olderHref ? (
        <Link href={olderHref} className="text-sm text-nx-link underline underline-offset-2">
          Older events
        </Link>
      ) : null}
    </div>
  );
}
