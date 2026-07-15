export type AccessDecision = "ALLOW" | "STEP_UP_AUTH" | "BLOCK";

export interface SessionEvent {
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
}

export interface AssessmentSummary {
  assessment_id: string;
  session_id: string;
  user_id: string;
  assessed_at: string;
  risk_score: number;
  decision: AccessDecision;
}

export interface Readiness {
  status: string;
  model: { fitted: boolean; version: string };
  pqc: { available: boolean; signature_algorithm: string | null };
}

