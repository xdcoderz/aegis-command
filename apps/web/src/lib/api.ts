import type {
  AssessmentReview,
  AssessmentSummary,
  AuditPage,
  AuditQuery,
  OverviewResponse,
  PolicyConfig,
  Readiness,
  ReceiptVerification,
  ResponseAction,
  SessionAction,
  SessionAssessment,
  SessionDetail,
  SessionEvent,
  SessionPage,
  SessionQuery,
  VaultEnvelope,
  VaultPlaintext,
  VaultStatus,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const ANALYST_API_KEY = import.meta.env.VITE_API_KEY as string | undefined;
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY as string | undefined;

function activeApiKey(): string | undefined {
  try {
    const raw = window.sessionStorage.getItem("aegis-command.demo.identity");
    const identity = raw ? JSON.parse(raw) as { role?: string } : null;
    return identity?.role === "SECURITY_ADMIN" ? ADMIN_API_KEY ?? ANALYST_API_KEY : ANALYST_API_KEY;
  } catch {
    return ANALYST_API_KEY;
  }
}

function demoActor(): string | undefined {
  try {
    const raw = window.sessionStorage.getItem("aegis-command.demo.identity");
    if (!raw) return undefined;
    const identity = JSON.parse(raw) as { displayName?: string };
    return identity.displayName;
  } catch {
    return undefined;
  }
}

function queryString(values: object): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = activeApiKey();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...(demoActor() ? { "X-Demo-Actor": demoActor() } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: string };
    throw new Error(body.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  readiness: () => request<Readiness>("/health/ready"),
  overview: () => request<OverviewResponse>("/overview"),
  sessions: (query: SessionQuery = {}) =>
    request<SessionPage>(`/sessions${queryString(query)}`),
  session: (sessionId: string) =>
    request<SessionDetail>(`/sessions/${encodeURIComponent(sessionId)}`),
  sessionAction: (sessionId: string, action: ResponseAction, note: string) =>
    request<SessionAction>(`/sessions/${encodeURIComponent(sessionId)}/action`, {
      method: "POST",
      body: JSON.stringify({ action, note }),
    }),
  policy: () => request<PolicyConfig>("/policies"),
  updatePolicy: (stepUpThreshold: number, blockThreshold: number) =>
    request<PolicyConfig>("/policies", {
      method: "PUT",
      body: JSON.stringify({
        step_up_threshold: stepUpThreshold,
        block_threshold: blockThreshold,
      }),
    }),
  audit: (query: AuditQuery = {}) =>
    request<AuditPage>(`/audit${queryString(query)}`),
  vaultStatus: () => request<VaultStatus>("/vault/status"),
  storeSecret: (plaintext: string) =>
    request<VaultEnvelope>("/vault/secrets", {
      method: "POST",
      body: JSON.stringify({ plaintext }),
    }),
  retrieveSecret: (envelopeId: string) =>
    request<VaultPlaintext>(`/vault/secrets/${encodeURIComponent(envelopeId)}/retrieve`, {
      method: "POST",
    }),
  recent: () => request<AssessmentSummary[]>("/assessments?limit=20"),
  assessment: (assessmentId: string) =>
    request<SessionAssessment>(`/assessments/${assessmentId}`),
  receipt: (assessmentId: string) =>
    request<ReceiptVerification>(`/assessments/${assessmentId}/receipt`),
  reviews: (assessmentId: string) =>
    request<AssessmentReview[]>(`/assessments/${assessmentId}/reviews`),
  createReview: (
    assessmentId: string,
    disposition: AssessmentReview["disposition"],
    comment: string,
  ) =>
    request<AssessmentReview>(`/assessments/${assessmentId}/reviews`, {
      method: "POST",
      body: JSON.stringify({ disposition, comment }),
    }),
  assess: (event: SessionEvent) =>
    request<SessionAssessment>("/assessments", {
      method: "POST",
      body: JSON.stringify(event),
    }),
};
