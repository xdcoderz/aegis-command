import { useEffect, useState } from "react";
import {
  AuditLogView,
  type AuditLogEntry,
} from "./components/enterprise/AuditLogView";
import {
  CommandCenter,
  type CommandCenterData,
  type SessionOperationalStatus,
} from "./components/enterprise/CommandCenter";
import { EnterpriseIcon, type EnterpriseIconName } from "./components/enterprise/EnterpriseIcon";
import {
  InvestigationView,
  type InvestigationSession,
  type InvestigationStatus,
  type ResponseAction as InvestigationAction,
  type ResponseActionResult,
} from "./components/enterprise/InvestigationView";
import {
  MockSsoLogin,
  type EnterpriseRole,
  type MockSsoIdentity,
} from "./components/enterprise/MockSsoLogin";
import { PolicyView, type RiskThresholdPolicy } from "./components/enterprise/PolicyView";
import { PqcVaultView } from "./components/enterprise/PqcVaultView";
import {
  defaultSessionFilters,
  SessionTriage,
  type SessionFilters,
  type SessionSort,
  type TriageSession,
  type TriageStatus,
} from "./components/enterprise/SessionTriage";
import { api } from "./lib/api";
import type {
  AuditItem,
  AuditPage,
  OverviewResponse,
  PolicyConfig,
  Readiness,
  ResponseAction,
  SessionDetail,
  SessionEvent,
  SessionListItem,
  SessionPage,
  VaultStatus,
} from "./types";

type View = "command" | "sessions" | "investigation" | "vault" | "audit" | "policies";
type DemoStage = "idle" | "observe" | "analyze" | "decide" | "prove" | "complete";

const SESSION_KEY = "finspark.demo.identity";
const PAGE_SIZE = 12;

const navigation: ReadonlyArray<{
  view: Exclude<View, "investigation">;
  label: string;
  icon: EnterpriseIconName;
}> = [
  { view: "command", label: "Command center", icon: "activity" },
  { view: "sessions", label: "Sessions", icon: "search" },
  { view: "vault", label: "PQC vault", icon: "key" },
  { view: "audit", label: "Audit log", icon: "check" },
  { view: "policies", label: "Policies", icon: "shield" },
];

const demoSteps: ReadonlyArray<{ stage: DemoStage; label: string; caption: string }> = [
  { stage: "observe", label: "Observe", caption: "Ingest telemetry" },
  { stage: "analyze", label: "Analyze", caption: "Compare baseline" },
  { stage: "decide", label: "Decide", caption: "Score access risk" },
  { stage: "prove", label: "Respond + record", caption: "Apply control; write audit" },
];

function storedIdentity(): MockSsoIdentity | null {
  try {
    const stored = window.sessionStorage.getItem(SESSION_KEY);
    return stored ? JSON.parse(stored) as MockSsoIdentity : null;
  } catch {
    return null;
  }
}

function wait(milliseconds: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));
}

function normalizedStatus(value: string): TriageStatus {
  const status = value.toUpperCase();
  if (status === "NORMAL" || status === "ACTIONED" || status === "ACTIVE") return status;
  if (status === "MONITORING") return "ACTIVE";
  if (status === "CONTAINED") return "ACTIONED";
  return "FLAGGED";
}

function investigationStatus(value: string): InvestigationStatus {
  return normalizedStatus(value);
}

function commandStatus(value: string): SessionOperationalStatus {
  return normalizedStatus(value);
}

function mapOverview(response: OverviewResponse, vault: VaultStatus | null): CommandCenterData {
  return {
    activeFlags: response.metrics.active_flags,
    sessionsMonitored24h: response.metrics.sessions_monitored_24h,
    averageRiskScore: response.metrics.average_risk_score,
    escalationsToday: response.metrics.escalation_count,
    pqcVault: {
      ready: response.metrics.vault_status === "QUANTUM_SAFE" || Boolean(vault?.quantum_safe),
      algorithm: response.metrics.vault_algorithm ?? vault?.kem_algorithm ?? "ML-KEM-768",
      encryptedItems: vault?.envelope_count ?? 0,
    },
    riskTrend: response.risk_trend.map((point) => point.average_risk),
    topRiskySessions: response.top_sessions.map((item) => ({
      sessionId: item.session_id,
      userId: item.user_id,
      role: item.role,
      resource: item.resource,
      occurredAt: item.started_at,
      riskScore: item.risk_score,
      status: commandStatus(item.status),
    })),
  };
}

function mapTriage(item: SessionListItem): TriageSession {
  return {
    sessionId: item.session_id,
    userId: item.user_id,
    role: item.role,
    startedAt: item.started_at,
    resource: item.resource,
    sourceIp: item.source_ip,
    riskScore: item.risk_score,
    status: normalizedStatus(item.status),
    decision: item.decision,
  };
}

function timelineKind(kind: string): "LOGIN" | "ACCESS" | "COMMAND" | "ESCALATION" | "LOGOUT" | "DECISION" {
  const normalized = kind.toUpperCase();
  if (normalized.includes("LOGIN") || normalized.includes("AUTH")) return "LOGIN";
  if (normalized.includes("COMMAND")) return "COMMAND";
  if (normalized.includes("ESCALAT")) return "ESCALATION";
  if (normalized.includes("LOGOUT")) return "LOGOUT";
  if (normalized.includes("DECISION") || normalized.includes("ASSESS") || normalized.includes("ANALYST")) return "DECISION";
  return "ACCESS";
}

function mapInvestigation(detail: SessionDetail, readiness: Readiness | null): InvestigationSession {
  const latestAction = detail.actions[0];
  return {
    sessionId: detail.session_id,
    userId: detail.user_id,
    role: detail.role,
    resource: detail.resource,
    sourceIp: detail.source_ip,
    deviceId: detail.device_id,
    startedAt: detail.started_at,
    endedAt: detail.ended_at,
    riskScore: detail.risk_score,
    status: investigationStatus(detail.status),
    modelVersion: readiness?.model.version,
    baselineScope: `identity:${detail.user_id}`,
    timeline: detail.timeline.map((event, index) => ({
      id: `${event.timestamp}-${index}`,
      label: event.title,
      timestamp: event.timestamp,
      detail: event.detail,
      kind: timelineKind(event.kind),
      severity: event.severity === "CRITICAL" || event.severity === "HIGH"
        ? "danger"
        : event.severity === "MEDIUM" ? "warning" : "neutral",
    })),
    baselineComparison: detail.baseline.map((metric) => ({
      key: metric.metric,
      label: metric.metric.replaceAll("_", " "),
      typical: `${Number(metric.baseline.toFixed(1))}${metric.unit}`,
      actual: `${Number(metric.actual.toFixed(1))}${metric.unit}`,
      anomalous: Math.abs(metric.deviation_percent) >= 25,
    })),
    riskFactors: detail.risk_factors.map((factor) => ({
      key: factor.key,
      label: factor.label,
      points: factor.score,
      evidence: factor.evidence,
      maxPoints: 60,
    })),
    rawLogs: detail.raw_logs.map((log) => ({
      timestamp: log.timestamp,
      source: log.event_type,
      message: Object.keys(log.metadata).length > 0
        ? `${log.message} | ${JSON.stringify(log.metadata)}`
        : log.message,
    })),
    response: latestAction ? {
      action: latestAction.action === "STEP_UP" ? "STEP_UP_AUTH" : latestAction.action,
      actor: latestAction.actor,
      actedAt: latestAction.acted_at,
      note: latestAction.note,
      reference: latestAction.enforcement_reference ?? undefined,
    } : null,
  };
}

function mapAudit(item: AuditItem): AuditLogEntry {
  const status = item.status.toUpperCase();
  return {
    id: item.id,
    timestamp: item.timestamp,
    sessionId: item.session_id,
    action: item.action || item.event_type,
    actor: item.actor,
    riskScore: item.risk_score,
    evidenceStatus: status.includes("FAIL") ? "FAILED" : status.includes("PEND") ? "PENDING" : "RECORDED",
  };
}

function demoAttackEvent(): SessionEvent {
  const now = Date.now();
  return {
    event_id: crypto.randomUUID(),
    session_id: `priv-attack-${now}`,
    user_id: "admin-00",
    role: "core-database-admin",
    occurred_at: new Date().toISOString(),
    source_ip: "198.51.100.77",
    device_id: "unmanaged-laptop-77",
    resource: "core-banking-master",
    resource_sensitivity: 1,
    commands: [
      "mimikatz credential::dump",
      "disable audit logging",
      "scp customer_dump.csv remote-host:/drop",
    ],
    session_duration_minutes: 84,
    privilege_level: 5,
    privilege_escalated: true,
    failed_auth_attempts: 7,
    bytes_transferred: 184_000_000,
    approved_for_baseline: false,
  };
}

function escapeCsv(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function downloadBlob(content: BlobPart, type: string, filename: string) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type }));
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(anchor.href), 500);
}

function exportAuditCsv(entries: AuditLogEntry[]) {
  const header = ["Timestamp", "Session", "Action", "Actor", "Risk score", "Record status"];
  const rows = entries.map((entry) => [
    entry.timestamp,
    entry.sessionId,
    entry.action,
    entry.actor,
    entry.riskScore,
    entry.evidenceStatus ?? "PENDING",
  ]);
  downloadBlob([header, ...rows].map((row) => row.map(escapeCsv).join(",")).join("\n"), "text/csv;charset=utf-8", "finspark-audit.csv");
}

function exportAuditPdf(entries: AuditLogEntry[]) {
  const safe = (value: string | number) => String(value).replace(/[<>&]/g, (character) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[character] ?? character);
  const rows = entries.map((entry) => `<tr><td>${safe(new Date(entry.timestamp).toLocaleString())}</td><td>${safe(entry.sessionId)}</td><td>${safe(entry.action)}</td><td>${safe(entry.actor)}</td><td>${safe(Math.round(entry.riskScore))}</td><td>${safe(entry.evidenceStatus ?? "PENDING")}</td></tr>`).join("");
  const report = window.open("", "finspark-audit-report", "width=1100,height=760");
  if (!report) throw new Error("Allow pop-ups to generate the printable PDF report.");
  report.document.write(`<!doctype html><html><head><title>FinSpark Sentinel audit log</title><style>body{font:12px Arial;color:#10213b;padding:34px}h1{margin:0 0 5px}p{color:#5f6f85;margin:0 0 24px}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #dbe2ec;text-align:left}th{font-size:10px;text-transform:uppercase;background:#f2f5f9}@media print{button{display:none}}</style></head><body><h1>FinSpark Sentinel audit log</h1><p>Generated ${safe(new Date().toLocaleString())} &middot; ${entries.length} records</p><table><thead><tr><th>Timestamp</th><th>Session</th><th>Action</th><th>Actor</th><th>Risk</th><th>Record status</th></tr></thead><tbody>${rows}</tbody></table><script>window.onload=()=>window.print()<\/script></body></html>`);
  report.document.close();
}

function DemoPipeline({ stage, onRun, busy }: { stage: DemoStage; onRun: () => void; busy: boolean }) {
  const order: DemoStage[] = ["observe", "analyze", "decide", "prove"];
  const current = stage === "complete" ? order.length : order.indexOf(stage);
  return (
    <section className={`judge-demo-strip ${busy ? "is-running" : ""}`} aria-live="polite">
      <div className="judge-demo-copy">
        <span>CONTROLLED TEST SCENARIO</span>
        <strong>{busy ? "Processing the test session" : "Test the full decision path"}</strong>
        <p>Run a synthetic misuse event through risk scoring, policy evaluation, response, and audit recording.</p>
      </div>
      <ol className="judge-demo-steps">
        {demoSteps.map((step, index) => {
          const state = stage === "complete" || current > index ? "done" : current === index ? "active" : "idle";
          return <li className={state} key={step.stage}><i>{state === "done" ? "✓" : index + 1}</i><span><strong>{step.label}</strong><small>{step.caption}</small></span></li>;
        })}
      </ol>
      <button className="demo-run-button" disabled={busy} onClick={onRun} type="button">
        {busy ? <><span className="button-spinner" /> Processing test session</> : <>Run misuse scenario <EnterpriseIcon name="arrow" size={16} /></>}
      </button>
    </section>
  );
}

export default function App() {
  const [identity, setIdentity] = useState<MockSsoIdentity | null>(storedIdentity);
  const [loginBusy, setLoginBusy] = useState(false);
  const [view, setView] = useState<View>("command");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [overviewResponse, setOverviewResponse] = useState<OverviewResponse | null>(null);
  const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionPage | null>(null);
  const [sessionFilters, setSessionFilters] = useState<SessionFilters>(defaultSessionFilters);
  const [sessionSort, setSessionSort] = useState<SessionSort>({ column: "riskScore", direction: "desc" });
  const [sessionPage, setSessionPage] = useState(1);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<SessionDetail | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<PolicyConfig | null>(null);
  const [auditPage, setAuditPage] = useState<AuditPage | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [demoStage, setDemoStage] = useState<DemoStage>("idle");
  const [demoBusy, setDemoBusy] = useState(false);

  const commandData = overviewResponse ? mapOverview(overviewResponse, vaultStatus) : null;

  async function loadOverview(silent = false) {
    if (!silent) setOverviewLoading(true);
    setOverviewError(null);
    try {
      const [health, overview, vault] = await Promise.all([
        api.readiness(),
        api.overview(),
        api.vaultStatus().catch(() => null),
      ]);
      setReadiness(health);
      setOverviewResponse(overview);
      setVaultStatus(vault);
    } catch (cause) {
      setOverviewError(cause instanceof Error ? cause.message : "The command center could not refresh.");
    } finally {
      setOverviewLoading(false);
    }
  }

  const sortKey = (sort: SessionSort) => {
    if (sort.column === "riskScore") return sort.direction === "desc" ? "risk_desc" : "risk_asc";
    if (sort.column === "startedAt") return sort.direction === "desc" ? "recent" : "oldest";
    const key = { userId: "user", resource: "resource", status: "status" }[sort.column];
    return `${key}_${sort.direction}`;
  };

  async function loadSessions(page = sessionPage, filters = sessionFilters, sort = sessionSort) {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      setSessions(await api.sessions({
        user: filters.user || undefined,
        resource: filters.resource || undefined,
        min_risk: filters.riskMin || undefined,
        date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00.000Z` : undefined,
        date_to: filters.dateTo ? `${filters.dateTo}T23:59:59.999Z` : undefined,
        sort: sortKey(sort),
        page,
        page_size: PAGE_SIZE,
      }));
      setSessionPage(page);
    } catch (cause) {
      setSessionsError(cause instanceof Error ? cause.message : "The session queue could not load.");
    } finally {
      setSessionsLoading(false);
    }
  }

  async function openSession(sessionId: string) {
    setView("investigation");
    window.scrollTo({ top: 0, behavior: "auto" });
    setInvestigationLoading(true);
    setInvestigationError(null);
    setInvestigation(null);
    try {
      setInvestigation(await api.session(sessionId));
    } catch (cause) {
      setInvestigationError(cause instanceof Error ? cause.message : "The investigation could not load.");
    } finally {
      setInvestigationLoading(false);
    }
  }

  async function loadPolicy() {
    try {
      setPolicy(await api.policy());
    } catch (cause) {
      setGlobalError(cause instanceof Error ? cause.message : "Policy settings are unavailable.");
    }
  }

  async function loadAudit() {
    setAuditLoading(true);
    try {
      setAuditPage(await api.audit({ page: 1, page_size: 200 }));
    } catch (cause) {
      setGlobalError(cause instanceof Error ? cause.message : "Audit evidence is unavailable.");
    } finally {
      setAuditLoading(false);
    }
  }

  async function navigate(next: View) {
    setView(next);
    window.scrollTo({ top: 0, behavior: "auto" });
    setGlobalError(null);
    if (next === "command") await loadOverview();
    if (next === "sessions") await loadSessions(1);
    if (next === "vault") {
      const status = await api.vaultStatus().catch(() => null);
      setVaultStatus(status);
    }
    if (next === "policies") await loadPolicy();
    if (next === "audit") await loadAudit();
  }

  useEffect(() => {
    if (!identity) return;
    void loadOverview();
  }, [identity]);

  useEffect(() => {
    if (!identity || view !== "command") return;
    const timer = window.setInterval(() => void loadOverview(true), 8_000);
    return () => window.clearInterval(timer);
  }, [identity, view]);

  async function login(nextIdentity: MockSsoIdentity) {
    setLoginBusy(true);
    await wait(450);
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(nextIdentity));
    setIdentity(nextIdentity);
    setLoginBusy(false);
  }

  function changeRole(role: EnterpriseRole) {
    if (!identity) return;
    const next = { ...identity, role };
    setIdentity(next);
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
  }

  async function runDemo() {
    setDemoBusy(true);
    setGlobalError(null);
    setDemoStage("observe");
    try {
      const request = api.assess(demoAttackEvent());
      await wait(420);
      setDemoStage("analyze");
      await wait(520);
      setDemoStage("decide");
      const result = await request;
      await wait(420);
      setDemoStage("prove");
      await loadOverview(true);
      await wait(500);
      setDemoStage("complete");
      await openSession(result.session_id);
    } catch (cause) {
      setDemoStage("idle");
      setGlobalError(cause instanceof Error ? cause.message : "The test scenario could not complete.");
    } finally {
      setDemoBusy(false);
    }
  }

  async function respond(action: InvestigationAction, note: string): Promise<ResponseActionResult> {
    if (!investigation) throw new Error("No active session selected.");
    const apiAction: ResponseAction = action === "STEP_UP_AUTH" ? "STEP_UP" : action;
    const result = await api.sessionAction(investigation.session_id, apiAction, note || `Action confirmed in FinSpark analyst console by ${identity?.displayName ?? "SOC analyst"}.`);
    setInvestigation(await api.session(investigation.session_id));
    void loadOverview(true);
    return {
      status: result.enforcement_status,
      reference: result.enforcement_reference ?? undefined,
      message: `${action.replaceAll("_", " ")} submitted · ${result.enforcement_status.replaceAll("_", " ")} · audit record stored.`,
    };
  }

  async function savePolicy(next: Pick<RiskThresholdPolicy, "stepUpThreshold" | "blockThreshold">): Promise<RiskThresholdPolicy> {
    const saved = await api.updatePolicy(next.stepUpThreshold, next.blockThreshold);
    setPolicy(saved);
    return {
      stepUpThreshold: saved.step_up_threshold,
      blockThreshold: saved.block_threshold,
      version: `v${saved.version}`,
      updatedAt: saved.updated_at,
    };
  }

  if (!identity) return <MockSsoLogin busy={loginBusy} onLogin={login} />;

  const ready = readiness?.status === "ready";
  const currentView = view === "investigation" ? "sessions" : view;

  return (
    <div className="sentinel-app">
      <aside className="app-sidebar">
        <button className="app-brand" onClick={() => void navigate("command")} type="button">
          <span className="brand-mark"><i />FS</span>
          <span><strong>FinSpark</strong><small>SENTINEL</small></span>
        </button>

        <div className="sidebar-context"><span>WORKSPACE</span><strong>Privileged access</strong><small>Demonstration environment</small></div>
        <nav aria-label="FinSpark product navigation">
          {navigation.map((item) => (
            <button className={currentView === item.view ? "active" : ""} key={item.view} onClick={() => void navigate(item.view)} type="button">
              <span><EnterpriseIcon name={item.icon} size={18} /></span>{item.label}
              {item.view === "sessions" && commandData && commandData.activeFlags > 0 && <b>{commandData.activeFlags}</b>}
            </button>
          ))}
        </nav>

        <div className="sidebar-proof">
          <div><span className={ready ? "online" : ""} /><strong>{ready ? "Services available" : "Connecting"}</strong></div>
          <p>{readiness?.model.version ?? "Behavior model warming"}</p>
          <small>{readiness?.enforcement.adapter ?? "Control plane"} · {readiness?.pqc.available ? "ML-DSA" : "local evidence"}</small>
        </div>
        <button className="sidebar-user" onClick={() => { window.sessionStorage.removeItem(SESSION_KEY); setIdentity(null); }} title="Sign out" type="button">
          <span>{identity.displayName.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span>
          <span><strong>{identity.displayName}</strong><small>{identity.role.replaceAll("_", " ")}</small></span>
          <i>↪</i>
        </button>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div className="environment-label"><i className={ready ? "online" : ""} /><span>FINSPARK BANK</span><b>/</b><strong>Security operations</strong></div>
          <div className="topbar-actions">
            <span className="live-clock"><EnterpriseIcon name="clock" size={14} /> Auto-refresh · every 8 seconds</span>
            <label className="role-switch"><span>View as</span><select aria-label="Switch operating role" onChange={(event) => changeRole(event.target.value as EnterpriseRole)} value={identity.role}><option value="SOC_ANALYST">SOC analyst</option><option value="SECURITY_ADMIN">Security admin</option></select></label>
            <span className="topbar-avatar">{identity.displayName.slice(0, 1)}</span>
          </div>
        </header>

        <div className="workflow-guide">
          <span><EnterpriseIcon name="shield" size={15} /> INVESTIGATION WORKFLOW</span>
          <ol><li className="active">Detect</li><li>Explain</li><li>Respond</li><li>Record</li></ol>
          <p>Move from an alert to a documented response using the same session record.</p>
        </div>

        <div className="app-content">
          {globalError && <div className="global-alert" role="alert"><EnterpriseIcon name="alert" size={18} /><span><strong>Request failed</strong>{globalError}</span><button onClick={() => setGlobalError(null)} type="button">Dismiss</button></div>}

          {view === "command" && <>
            <DemoPipeline busy={demoBusy} onRun={() => void runDemo()} stage={demoStage} />
            <CommandCenter
              data={commandData}
              error={overviewError}
              lastUpdated={overviewResponse?.generated_at ?? null}
              loading={overviewLoading}
              onOpenSession={(id) => void openSession(id)}
              onOpenSessions={() => void navigate("sessions")}
              onOpenVault={() => void navigate("vault")}
              onRefresh={() => loadOverview()}
            />
          </>}

          {view === "sessions" && <SessionTriage
            error={sessionsError}
            filters={sessionFilters}
            items={(sessions?.items ?? []).map(mapTriage)}
            loading={sessionsLoading}
            onApplyFilters={() => loadSessions(1)}
            onClearFilters={() => { const cleared = defaultSessionFilters(); setSessionFilters(cleared); void loadSessions(1, cleared); }}
            onFiltersChange={setSessionFilters}
            onOpenSession={(id) => void openSession(id)}
            onPageChange={(page) => void loadSessions(page)}
            onRetry={() => loadSessions()}
            onSortChange={(sort) => { setSessionSort(sort); void loadSessions(1, sessionFilters, sort); }}
            page={sessions?.page ?? sessionPage}
            pageSize={sessions?.page_size ?? PAGE_SIZE}
            sort={sessionSort}
            total={sessions?.total ?? 0}
          />}

          {view === "investigation" && <InvestigationView
            analystName={identity.displayName}
            error={investigationError}
            loading={investigationLoading}
            onBack={() => void navigate("sessions")}
            onRespond={respond}
            onRetry={() => { if (investigation) void openSession(investigation.session_id); }}
            session={investigation ? mapInvestigation(investigation, readiness) : null}
          />}

          {view === "vault" && <PqcVaultView
            onDecrypt={(envelopeId) => api.retrieveSecret(envelopeId)}
            onEncrypt={async (plaintext) => {
              const envelope = await api.storeSecret(plaintext);
              setVaultStatus(await api.vaultStatus());
              return envelope;
            }}
            summary={{
              available: vaultStatus?.available ?? false,
              quantumSafe: vaultStatus?.quantum_safe ?? false,
              algorithm: vaultStatus?.kem_algorithm ?? "ML-KEM-768 + AES-256-GCM",
              itemCount: vaultStatus?.envelope_count ?? 0,
              provider: vaultStatus?.mode ?? "Open Quantum Safe",
            }}
            readOnly={identity.role !== "SECURITY_ADMIN"}
          />}

          {view === "policies" && <PolicyView
            onSave={savePolicy}
            readOnly={identity.role !== "SECURITY_ADMIN"}
            policy={{
              stepUpThreshold: policy?.step_up_threshold ?? 45,
              blockThreshold: policy?.block_threshold ?? 75,
              version: policy ? `v${policy.version}` : "loading",
              updatedAt: policy?.updated_at,
            }}
          />}

          {view === "audit" && <AuditLogView
            entries={(auditPage?.items ?? []).map(mapAudit)}
            loading={auditLoading}
            onExportCsv={exportAuditCsv}
            onExportPdf={exportAuditPdf}
            onOpenSession={(id) => void openSession(id)}
          />}
        </div>
      </main>
    </div>
  );
}
