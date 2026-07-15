import type { AssessmentSummary, Readiness, SessionAssessment, SessionEvent } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  readiness: () => request<Readiness>("/health/ready"),
  recent: () => request<AssessmentSummary[]>("/assessments?limit=20"),
  assess: (event: SessionEvent) =>
    request<SessionAssessment>("/assessments", {
      method: "POST",
      body: JSON.stringify(event),
    }),
};

