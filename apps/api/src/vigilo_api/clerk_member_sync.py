"""`python -m vigilo_api.clerk_member_sync` (run hourly by cron inside the API container).

ADR-0014: an organisation linked to a Clerk organisation follows Clerk's member list, so
someone removed there loses access here too. Runs in the API, not the scanner, because the
scanner is deliberately cut off from the network. Fail-safe: an organisation whose list
cannot be read, is empty, or no longer exists in Clerk is left alone; owners are never removed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from vigilo_identity.repository import list_clerk_linked_orgs, remove_members_missing_from_clerk
from vigilo_integrations.clerk import list_clerk_org_member_ids
from vigilo_integrations.errors import IdentityProviderError
from vigilo_persistence import session_scope
from vigilo_security.audit import AuditEvent, audit

Fetch = Callable[[str], Awaitable[set[str] | None]]


@dataclass
class SyncResult:
    organisations: int = 0
    removed: int = 0
    skipped: int = 0


async def sync_clerk_members(fetch: Fetch = list_clerk_org_member_ids) -> SyncResult:
    result = SyncResult()
    async with session_scope() as session:
        orgs = await list_clerk_linked_orgs(session)
    for org in orgs:
        result.organisations += 1
        try:
            ids = await fetch(org.clerk_org_id)
        except IdentityProviderError:
            ids = None
        if not ids:
            result.skipped += 1
            continue
        async with session_scope() as session:
            removed = await remove_members_missing_from_clerk(session, org, ids)
            for account in removed:
                await audit(
                    session,
                    AuditEvent(
                        actor="clerk-member-sync",
                        action="member_removed_by_clerk",
                        subject=str(account.id),
                        account_id=account.id,
                        org_id=org.id,
                        metadata={"clerk_org_id": org.clerk_org_id},
                    ),
                )
        result.removed += len(removed)
    return result


def main() -> None:
    result = asyncio.run(sync_clerk_members())
    print(
        f"clerk member sync: {result.organisations} organisations, "
        f"{result.removed} members removed, {result.skipped} skipped"
    )


if __name__ == "__main__":
    main()
