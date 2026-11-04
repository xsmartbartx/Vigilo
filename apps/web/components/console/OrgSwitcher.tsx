import Link from "next/link";
import { switchOrg } from "../../app/console/actions";
import type { Org } from "../../lib/nexora/data";
import { Badge, Button } from "../ui";

// A plain form: works without client JS. The select posts the chosen org to a
// server action, which checks membership before remembering it.
export function OrgSwitcher({ orgs, active }: { orgs: Org[]; active: Org }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <form action={switchOrg} className="flex min-w-0 max-w-full flex-wrap items-center gap-2">
        <label htmlFor="org-switcher" className="text-nx-text-muted">
          Organisation
        </label>
        <select
          id="org-switcher"
          name="org_id"
          defaultValue={active.id}
          className="h-8 w-56 max-w-full min-w-0 truncate rounded-nx-md border border-nx-border-input bg-nx-bg px-2 text-nx-text focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-nx-accent"
        >
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        <Button type="submit" size="sm" variant="secondary">
          Switch
        </Button>
      </form>
      <Badge>{active.role}</Badge>
      <Link href="/console/new-org" className="text-nx-link underline underline-offset-2">
        New organisation
      </Link>
    </div>
  );
}
