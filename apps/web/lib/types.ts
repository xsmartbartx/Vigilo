// TypeScript mirrors of apps/api/src/vigilo_api/schemas.py. Kept in sync by
// hand for now — no codegen this phase.

export type Severity = "critical" | "high" | "medium" | "low" | "info" | "passed";
export type Confidence = "confirmed" | "indicated";
export type Verdict = "passed" | "failed" | "inconclusive" | "not_applicable";
export type Tier = "passive" | "active";

export interface ScanSubmissionResponse {
  scan_job_id: string;
  status: string;
  granted_tier: Tier;
}

export interface ScanStatusResponse {
  scan_job_id: string;
  status: string;
  target_origin: string;
  tier: Tier;
  score: number | null;
  grade: string | null;
  counts_by_severity: Partial<Record<Severity, number>> | null;
  finished_at: string | null;
}

export interface EvidenceResponse {
  matched_indicator: string | null;
  request_summary: string | null;
  redaction_applied: boolean | null;
  captured_at: string;
}

export type EstimatedEffort = "trivial" | "small" | "medium" | "large";

export interface RemediationResponse {
  source: "template" | "llm";
  explanation: string;
  impact: string;
  remediation_steps: string[];
  agent_prompt: string;
  estimated_effort: EstimatedEffort | null;
}

export interface ReportFindingResponse {
  check_id: string;
  category: string;
  title: string;
  severity: Severity;
  confidence: Confidence;
  verdict: Verdict;
  summary: string;
  remediation: RemediationResponse;
  references: string[];
  evidence: EvidenceResponse | null;
  fingerprint: string;
  suppressed: boolean;
  why_here?: string | null;
}

export interface BrandingProfileResponse {
  logo_url: string | null;
  primary_color: string | null;
  footer_text: string | null;
  custom_domain: string | null;
}

export interface ScanReportResponse {
  scan_job_id: string | null;
  target_id: string | null;
  is_owner: boolean | null;
  can_accept_risk?: boolean | null;
  stack?: string[];
  target_origin: string;
  registry_version: string;
  score: number;
  grade: string;
  counts_by_severity: Partial<Record<Severity, number>>;
  generated_at: string;
  findings: ReportFindingResponse[];
  branding: BrandingProfileResponse | null;
}

export interface PdfStatusResponse {
  report_id: string;
  status: "pending" | "complete" | "failed";
  download_url: string | null;
}

export interface ShareLinkCreateResponse {
  share_link_id: string;
  token: string;
  url: string;
  expires_at: string | null;
}

export interface ShareLinkResponse {
  share_link_id: string;
  expires_at: string | null;
  revoked_at: string | null;
  view_count: number;
  created_at: string;
}

export interface EntitlementsResponse {
  plan_id: string;
  targets_limit: number | null;
  scans_per_month_limit: number | null;
  active_tier_allowed: boolean;
  share_links_allowed: boolean;
  monitoring_frequency: string | null;
  monitors_limit: number | null;
  api_keys_limit: number | null;
  api_rate_limit_per_minute: number | null;
  white_label_allowed: boolean;
  repo_connectors_limit: number | null;
}

export interface AccountResponse {
  account_id: string;
  email: string;
  status: string;
  created_at: string;
  entitlements: EntitlementsResponse;
}

export interface PlanResponse {
  plan_id: string;
  targets_limit: number | null;
  scans_per_month_limit: number | null;
  active_tier_allowed: boolean;
  share_links_allowed: boolean;
  monitoring_frequency: string | null;
  monitors_limit: number | null;
  api_keys_limit: number | null;
  api_rate_limit_per_minute: number | null;
  white_label_allowed: boolean;
  repo_connectors_limit: number | null;
  price_cents: number;
  price_cents_yearly: number;
  currency: string;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

export type VerificationMethod = "dns_txt" | "wellknown_file" | "meta_tag" | "email";

export interface VerificationInitiateResponse {
  proof_id: string;
  method: VerificationMethod;
  nonce: string;
  instructions: string;
}

export interface VerificationCheckResponse {
  proof_id: string;
  status: string;
}

export interface ApiKeyResponse {
  api_key_id: string;
  name: string;
  prefix: string;
  scopes: string[];
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface ApiKeyCreateResponse {
  api_key_id: string;
  name: string;
  prefix: string;
  scopes: string[];
  api_key: string; // plaintext — present only in this response, once
}

export interface TargetResponse {
  // Set on the single-target read only.
  org_entitlements?: EntitlementsResponse | null;
  target_id: string;
  origin: string;
  verification_status: Tier;
  verified_at: string | null;
  verification_method: string | null;
}

export interface MonitorResponse {
  monitor_id: string;
  target_id: string;
  cadence_hours: number;
  enabled: boolean;
  next_run_at: string;
  quiet_start_utc: number | null;
  quiet_end_utc: number | null;
}

export interface ScoreHistoryEntry {
  scan_id: string;
  score: number;
  grade: string;
  registry_version: string;
  created_at: string;
}

export type AlertType =
  | "new_critical"
  | "new_high"
  | "regressed"
  | "cert_expiry"
  | "score_drop"
  | "scan_failed";

export interface AlertResponse {
  alert_id: string;
  type: AlertType;
  severity: Severity | null;
  fingerprint: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface SuppressionResponse {
  suppression_id: string;
  target_id: string;
  fingerprint: string;
  check_id: string;
  reason: string;
  expires_at: string | null;
  created_by_account_id: string;
  created_at: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  context?: Record<string, unknown>;
}

export interface OrgResponse {
  org_id: string;
  name: string;
  slug: string;
  is_personal: boolean;
  role: "owner" | "admin" | "member" | "viewer";
  entitlements: EntitlementsResponse;
  is_claimed?: boolean;
}

export interface OrgMemberResponse {
  account_id: string;
  email: string;
  role: string;
}

export interface OrgProductResponse {
  slug: string;
  enabled: boolean;
  available: boolean;
}

export interface OrgUsageResponse {
  product_slug: string;
  meter: string;
  used: number;
  limit: number | null;
  period_start: string;
}

export interface OrgInviteResponse {
  invite_id: string;
  email: string;
  role: string;
  expires_at: string;
  created_at: string;
}

export interface OrgInviteCreateResponse {
  invite_id: string;
  email: string;
  role: string;
  expires_at: string;
  token: string;
  email_status: "sent" | "not_configured" | "rate_limited" | "failed";
}

export interface BillingProductLine {
  product_slug: string;
  product_name: string;
  plan_id: string;
  status: "active" | "free";
  interval: "month" | "year" | null;
  amount_cents: number;
  currency: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  can_purchase: boolean;
}

export interface BillingSummaryResponse {
  org_id: string;
  org_name: string;
  products: BillingProductLine[];
  totals: { monthly_cents: number; yearly_cents: number; currency: string };
}

export interface AuditEntryResponse {
  event_id: string;
  occurred_at: string;
  action: string;
  subject: string;
  actor_kind: "person" | "system";
  actor_label: string;
  details: Record<string, unknown>;
}

export interface AuditPageResponse {
  events: AuditEntryResponse[];
  next_cursor: string | null;
  actions: string[];
}

export interface DeletionBlocker {
  kind: "members" | "subscription";
  org_id: string;
  org_name: string;
  detail: string;
}

export interface DeleteAccountResponse {
  deleted: boolean;
  identity_removed: boolean;
  storage_cleanup: string;
}
