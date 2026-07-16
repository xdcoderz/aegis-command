export type AccessDecision = "ALLOW" | "STEP_UP_AUTH" | "BLOCK";
export type ResponseAction = "ALLOW" | "STEP_UP" | "BLOCK";
export type EnforcementStatus = "PENDING" | "NOT_CONFIGURED" | "SUCCEEDED" | "FAILED";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface SessionEvent {
  event_id?: string;
  session_id: string;
  user_id: string;
  role: string;
  occurred_at: string;
  source_ip: string;
  device_id: string;
  resource: string;
  resource_sensitivity: number;
  commands: string[];
  session_duration_minutes: number;
  privilege_level: number;
  privilege_escalated: boolean;
  failed_auth_attempts: number;
  bytes_transferred: number;
  approved_for_baseline?: boolean;
}

export interface RiskFactor {
  key: string;
  label: string;
  score: number;
  evidence: string;
}

export interface SessionAssessment {
  assessment_id: string;
  event_id: string;
  session_id: string;
  user_id: string;
  assessed_at: string;
  anomaly_score: number;
  risk_score: number;
  decision: AccessDecision;
  factors: RiskFactor[];
  features: Record<string, number>;
  model_version: string;
  baseline_scope: string;
  audit_signature: string | null;
  signature_algorithm: string | null;
  enforcement_status: EnforcementStatus;
  enforcement_reference: string | null;
  enforcement_error: string | null;
  enforced_at: string | null;
}

export interface AssessmentSummary {
  assessment_id: string;
  session_id: string;
  user_id: string;
  assessed_at: string;
  risk_score: number;
  decision: AccessDecision;
  enforcement_status: EnforcementStatus;
}

export interface Readiness {
  status: string;
  model: { fitted: boolean; version: string };
  pqc: { available: boolean; signature_algorithm: string | null };
  database: { ready: boolean };
  authentication: { enabled: boolean; configured_principals: number };
  enforcement: { adapter: string };
}

export interface ReceiptVerification {
  assessment_id: string;
  valid: boolean;
  algorithm: string | null;
  payload_sha256: string;
  verified_at: string;
}

export interface AssessmentReview {
  review_id: string;
  assessment_id: string;
  reviewer: string;
  disposition: "EXPECTED" | "BENIGN" | "SUSPICIOUS" | "MALICIOUS";
  comment: string;
  reviewed_at: string;
}

export interface SessionListItem {
  assessment_id: string;
  session_id: string;
  user_id: string;
  role: string;
  started_at: string;
  assessed_at: string;
  resource: string;
  source_ip: string;
  risk_score: number;
  severity: Severity;
  decision: AccessDecision;
  status: string;
  enforcement_status: EnforcementStatus;
}

export interface RiskTrendPoint {
  timestamp: string;
  average_risk: number;
  count: number;
}

export interface OverviewResponse {
  generated_at: string;
  metrics: {
    active_flags: number;
    sessions_monitored_24h: number;
    average_risk_score: number;
    escalation_count: number;
    vault_status: string;
    vault_algorithm: string | null;
  };
  risk_trend: RiskTrendPoint[];
  top_sessions: SessionListItem[];
}

export interface SessionQuery {
  user?: string;
  resource?: string;
  min_risk?: number;
  max_risk?: number;
  decision?: AccessDecision | "";
  status?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export interface SessionPage {
  items: SessionListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface TimelineEvent {
  timestamp: string;
  kind: string;
  title: string;
  detail: string;
  severity: Severity;
}

export interface BaselineMetric {
  metric: string;
  baseline: number;
  actual: number;
  unit: string;
  deviation_percent: number;
}

export interface RawLog {
  timestamp: string;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
}

export interface SessionAction {
  action_id: string;
  assessment_id: string;
  session_id: string;
  action: ResponseAction;
  actor: string;
  note: string;
  acted_at: string;
  enforcement_status: EnforcementStatus;
  enforcement_reference: string | null;
  enforcement_error: string | null;
}

export interface SessionDetail {
  assessment_id: string;
  session_id: string;
  user_id: string;
  role: string;
  started_at: string;
  ended_at: string;
  assessed_at: string;
  resource: string;
  source_ip: string;
  device_id: string;
  risk_score: number;
  severity: Severity;
  decision: AccessDecision;
  status: string;
  enforcement_status: EnforcementStatus;
  timeline: TimelineEvent[];
  baseline: BaselineMetric[];
  risk_factors: RiskFactor[];
  raw_logs: RawLog[];
  reviews: AssessmentReview[];
  actions: SessionAction[];
}

export interface PolicyConfig {
  step_up_threshold: number;
  block_threshold: number;
  version: number;
  updated_at: string;
  updated_by: string;
}

export interface AuditItem {
  id: string;
  timestamp: string;
  session_id: string;
  assessment_id: string;
  event_type: string;
  action: string;
  actor: string;
  risk_score: number;
  detail: string;
  status: string;
}

export interface AuditQuery {
  session_id?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface AuditPage {
  items: AuditItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface VaultStatus {
  available: boolean;
  quantum_safe?: boolean;
  signature_algorithm: string | null;
  kem_algorithm?: string | null;
  envelope_count?: number;
  mode?: string;
}

export interface VaultEnvelope {
  envelope_id: string;
  algorithm: string;
  ciphertext: string;
}

export interface VaultPlaintext {
  envelope_id: string;
  plaintext: string;
}
