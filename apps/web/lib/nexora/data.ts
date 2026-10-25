// Console data layer: server-side calls to apps/api's org endpoints, scoped
// to the caller's Clerk session. The active org is remembered in a cookie,
// but the cookie is only a preference: it is honoured only if the id is in
// the caller's own org list, and the API re-checks membership on every call.
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";
import { api } from "../api";
import type { AuditPageResponse, EntitlementsResponse } from "../types";
import type { ProductSlug } from "./catalog";

export const ACTIVE_ORG_COOKIE = "nx_org";
const JWT_TEMPLATE = process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE ?? "vigilo-api";

export type Role = "owner" | "admin" | "member" | "viewer";

export interface Org {
  id: string;
  name: string;
  slug: string;
  isPersonal: boolean;
  role: Role;
  // The organisation's plan limits (its owner's plan), not the caller's.
  entitlements: EntitlementsResponse;
  // The Clerk organisation active in the session, which opens by default.
  isClaimed: boolean;
}

export interface ProductState {
  slug: ProductSlug;
  enabled: boolean;
  // False when this build cannot run the product yet: it cannot be enabled.
  available: boolean;
}

export interface UsageRow {
  slug: ProductSlug;
  meter: string;
  used: number;
  limit: number | null;
  resetsOn: string;
}

export interface Member {
  accountId: string;
  email: string;
  role: Role;
}

export async function sessionToken(): Promise<string> {
  const { getToken } = await auth();
  const token = await getToken({ template: JWT_TEMPLATE });
  if (!token) redirect("/sign-in");
  return token;
}

export async function listMyOrgs(): Promise<Org[]> {
  const orgs = await api.listOrgs(await sessionToken());
  return orgs.map((o) => ({
    id: o.org_id,
    name: o.name,
    slug: o.slug,
    isPersonal: o.is_personal,
    role: o.role,
    entitlements: o.entitlements,
    isClaimed: o.is_claimed ?? false,
  }));
}

export async function getActiveOrg(): Promise<Org> {
  const orgs = await listMyOrgs();
  const wanted = (await cookies()).get(ACTIVE_ORG_COOKIE)?.value;
  // An explicit choice wins, then the Clerk organisation active in the session, then the
  // first one. GET /v1/orgs always returns at least the personal org.
  return orgs.find((o) => o.id === wanted) ?? orgs.find((o) => o.isClaimed) ?? orgs[0];
}

export async function listProductStates(orgId: string): Promise<ProductState[]> {
  const rows = await api.listOrgProducts(orgId, await sessionToken());
  return rows.map((r) => ({
    slug: r.slug as ProductSlug,
    enabled: r.enabled,
    available: r.available,
  }));
}

export async function listUsage(orgId: string): Promise<UsageRow[]> {
  const rows = await api.getOrgUsage(orgId, await sessionToken());
  return rows.map((r) => ({
    slug: r.product_slug as ProductSlug,
    meter: r.meter === "scans" ? "Scans this month" : `${r.meter} this month`,
    used: r.used,
    limit: r.limit,
    resetsOn: "1st of next month (UTC)",
  }));
}

export async function listMembers(orgId: string): Promise<Member[]> {
  const rows = await api.listOrgMembers(orgId, await sessionToken());
  return rows.map((m) => ({ accountId: m.account_id, email: m.email, role: m.role as Role }));
}

export interface PendingInvite {
  id: string;
  email: string;
  role: Role;
  expiresAt: string;
  expired: boolean;
}

export async function listPendingInvites(orgId: string): Promise<PendingInvite[]> {
  const rows = await api.listOrgInvites(orgId, await sessionToken());
  const now = Date.now();
  return rows.map((i) => ({
    id: i.invite_id,
    email: i.email,
    role: i.role as Role,
    expiresAt: i.expires_at,
    expired: new Date(i.expires_at).getTime() < now,
  }));
}

export async function currentAccountId(): Promise<string> {
  return (await api.getMe(await sessionToken())).account_id;
}

export async function loadAuditPage(
  orgId: string,
  query: { cursor?: string; action?: string },
): Promise<AuditPageResponse> {
  return api.getAuditLog(orgId, await sessionToken(), { ...query, limit: 50 });
}
