import { useEffect, useState } from "react";
import { EnterpriseIcon } from "./EnterpriseIcon";
import { formatClock, formatCompactDate, riskLabel, riskTier } from "./risk";
import "./enterprise.css";

export type ResponseAction = "ALLOW" | "STEP_UP_AUTH" | "BLOCK";
export type InvestigationStatus = "NORMAL" | "FLAGGED" | "ACTIONED" | "ACTIVE";

export interface InvestigationTimelineEvent {
  id: string;
  label: string;
  timestamp: string;
  detail: string;
  kind: "LOGIN" | "ACCESS" | "COMMAND" | "ESCALATION" | "LOGOUT" | "DECISION";
  severity?: "neutral" | "warning" | "danger";
}

export interface BaselineComparison {
  key: string;
  label: string;
  typical: string;
  actual: string;
  anomalous: boolean;
}

export interface InvestigationRiskFactor {
  key: string;
  label: string;
  points: number;
  evidence: string;
  maxPoints?: number;
}

export interface RawLogEntry {
  timestamp: string;
  source: string;
  message: string;
}

export interface ResponseRecord {
  action: ResponseAction;
  actor: string;
  actedAt: string;
  note?: string;
  reference?: string;
}

export interface InvestigationSession {
  sessionId: string;
  userId: string;
  role: string;
  resource: string;
  sourceIp: string;
  deviceId?: string;
  startedAt: string;
  endedAt?: string | null;
  riskScore: number;
  status: InvestigationStatus;
  modelVersion?: string;
  baselineScope?: string;
  timeline: InvestigationTimelineEvent[];
  baselineComparison: BaselineComparison[];
  riskFactors: InvestigationRiskFactor[];
  rawLogs: RawLogEntry[];
  response?: ResponseRecord | null;
}

export interface ResponseActionResult {
  status?: string;
  message?: string;
  reference?: string;
}

export interface InvestigationViewProps {
  session: InvestigationSession | null;
  loading?: boolean;
  error?: string | null;
  analystName?: string;
  onBack?: () => void;
  onRetry?: () => void | Promise<void>;
  onRespond: (action: ResponseAction, note: string) => void | ResponseActionResult | Promise<void | ResponseActionResult>;
}

const actionDetails: ReadonlyArray<{
  action: ResponseAction;
  label: string;
  description: string;
  icon: "check" | "shield" | "alert";
}> = [
  { action: "ALLOW", label: "Allow", description: "Continue under monitoring", icon: "check" },
  { action: "STEP_UP_AUTH", label: "Step-up auth", description: "Challenge identity now", icon: "shield" },
  { action: "BLOCK", label: "Block", description: "Terminate privileged access", icon: "alert" },
];

function InvestigationSkeleton() {
  return (
    <div aria-label="Loading investigation" className="enterprise-investigation-skeleton" role="status">
      <span className="enterprise-skeleton enterprise-skeleton-title" />
      <span className="enterprise-skeleton enterprise-skeleton-timeline" />
      <div><span className="enterprise-skeleton enterprise-skeleton-panel" /><span className="enterprise-skeleton enterprise-skeleton-panel" /></div>
    </div>
  );
}

export function InvestigationView({
  session,
  loading = false,
  error = null,
  analystName = "SOC analyst",
  onBack,
  onRetry,
  onRespond,
}: InvestigationViewProps) {
  const [note, setNote] = useState("");
  const [pendingAction, setPendingAction] = useState<ResponseAction | null>(null);
  const [responseMessage, setResponseMessage] = useState<string | null>(null);
  const [responseError, setResponseError] = useState<string | null>(null);

  useEffect(() => {
    setNote("");
    setPendingAction(null);
    setResponseMessage(null);
    setResponseError(null);
  }, [session?.sessionId]);

  if (loading && !session) return <InvestigationSkeleton />;

  if (error && !session) {
    return (
      <section className="enterprise-state enterprise-state-error" role="alert">
        <span className="enterprise-state-icon"><EnterpriseIcon name="alert" size={22} /></span>
        <div><strong>Investigation could not be loaded</strong><p>{error}</p></div>
        {onRetry && <button className="enterprise-button enterprise-button-secondary" onClick={() => void onRetry()} type="button">Retry</button>}
      </section>
    );
  }

  if (!session) {
    return (
      <section className="enterprise-state">
        <span className="enterprise-state-icon"><EnterpriseIcon name="search" size={22} /></span>
        <div><strong>Select a session to investigate</strong><p>Open a record from the command center or session queue.</p></div>
      </section>
    );
  }

  const tier = riskTier(session.riskScore);
  const submitResponse = async (action: ResponseAction) => {
    setPendingAction(action);
    setResponseError(null);
    setResponseMessage(null);
    try {
      const result = await onRespond(action, note.trim());
      setResponseMessage(result?.message ?? `${action.replaceAll("_", " ")} response submitted and written to the audit log.`);
    } catch (responseActionError) {
      setResponseError(responseActionError instanceof Error ? responseActionError.message : "The response control plane rejected this action.");
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <section aria-labelledby="investigation-title" className="enterprise-view enterprise-investigation">
      <header className="enterprise-investigation-header">
        <div className="enterprise-investigation-heading">
          {onBack && <button className="enterprise-back-button" onClick={onBack} type="button">← Session queue</button>}
          <span className="enterprise-eyebrow"><EnterpriseIcon name="search" size={14} /> SESSION INVESTIGATION</span>
          <h1 id="investigation-title">{session.userId} <span>/ {session.role}</span></h1>
          <div className="enterprise-session-metadata">
            <span><small>Session ID</small><strong>{session.sessionId}</strong></span>
            <span><small>Protected resource</small><strong>{session.resource}</strong></span>
            <span><small>Origin</small><strong>{session.sourceIp}{session.deviceId ? ` · ${session.deviceId}` : ""}</strong></span>
            <span><small>Observed window</small><strong>{formatCompactDate(session.startedAt)} – {session.endedAt ? formatClock(session.endedAt) : "Live"}</strong></span>
          </div>
        </div>
        <div className={`enterprise-investigation-score enterprise-risk-${tier}`}>
          <span>{riskLabel(session.riskScore)} risk</span>
          <strong>{Math.round(session.riskScore)}<small>/100</small></strong>
          <em>{session.status}</em>
        </div>
      </header>

      {error && <div className="enterprise-inline-alert" role="status"><EnterpriseIcon name="alert" size={15} /> Session refreshed with partial data. {error}</div>}

      <article className="enterprise-panel enterprise-timeline-panel">
        <div className="enterprise-panel-header">
          <div><span className="enterprise-kicker">Evidence sequence</span><h2>Session timeline</h2></div>
          <span className="enterprise-proof-label"><EnterpriseIcon name="activity" size={15} /> {session.timeline.length} correlated events</span>
        </div>
        {session.timeline.length === 0 ? (
          <div className="enterprise-compact-empty"><EnterpriseIcon name="clock" /><strong>No correlated events</strong><span>Raw telemetry is still being processed.</span></div>
        ) : (
          <div className="enterprise-timeline-scroll">
            <ol className="enterprise-timeline">
              {session.timeline.map((event, index) => (
                <li className={`enterprise-timeline-${event.severity ?? "neutral"}`} key={event.id}>
                  <span className="enterprise-timeline-index">{String(index + 1).padStart(2, "0")}</span>
                  <i aria-hidden="true" />
                  <time dateTime={event.timestamp}>{formatClock(event.timestamp)}</time>
                  <strong>{event.label}</strong>
                  <p>{event.detail}</p>
                  <small>{event.kind.replaceAll("_", " ")}</small>
                </li>
              ))}
            </ol>
          </div>
        )}
      </article>

      <div className="enterprise-investigation-grid">
        <div className="enterprise-investigation-evidence">
          <article className="enterprise-panel enterprise-baseline-panel">
            <div className="enterprise-panel-header">
              <div><span className="enterprise-kicker">Behavior analytics</span><h2>Baseline vs this session</h2></div>
              {session.baselineScope && <span className="enterprise-proof-label">Scope: {session.baselineScope}</span>}
            </div>
            {session.baselineComparison.length === 0 ? (
              <div className="enterprise-compact-empty"><EnterpriseIcon name="activity" /><strong>Insufficient baseline history</strong><span>More identity activity is needed for comparison.</span></div>
            ) : (
              <div className="enterprise-comparison-table" role="table" aria-label="Behavior baseline comparison">
                <div className="enterprise-comparison-head" role="row"><span role="columnheader">Signal</span><span role="columnheader">Typical behavior</span><span role="columnheader">This session</span></div>
                {session.baselineComparison.map((comparison) => (
                  <div className={comparison.anomalous ? "is-anomalous" : undefined} key={comparison.key} role="row">
                    <strong role="cell">{comparison.label}</strong>
                    <span role="cell">{comparison.typical}</span>
                    <span role="cell"><i aria-hidden="true" />{comparison.actual}<small>{comparison.anomalous ? "Deviation" : "Expected"}</small></span>
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="enterprise-panel enterprise-factors-panel">
            <div className="enterprise-panel-header">
              <div><span className="enterprise-kicker">Decision evidence</span><h2>Risk factor breakdown</h2></div>
              {session.modelVersion && <span className="enterprise-proof-label">Model {session.modelVersion}</span>}
            </div>
            {session.riskFactors.length === 0 ? (
              <div className="enterprise-compact-empty"><EnterpriseIcon name="check" /><strong>No risk factors returned</strong><span>No factor-level detail was returned for this assessment.</span></div>
            ) : (
              <div className="enterprise-factor-list">
                {session.riskFactors.map((factor, index) => {
                  const maxPoints = Math.max(1, factor.maxPoints ?? 40);
                  const width = Math.max(3, Math.min(100, (Math.abs(factor.points) / maxPoints) * 100));
                  return (
                    <div className="enterprise-factor-row" key={factor.key}>
                      <span className="enterprise-factor-rank">{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <div className="enterprise-factor-title"><strong>{factor.label}</strong><span>{factor.points >= 0 ? "+" : ""}{factor.points.toFixed(1)} pts</span></div>
                        <div aria-label={`${factor.label}, ${factor.points} risk points`} aria-valuemax={maxPoints} aria-valuemin={0} aria-valuenow={Math.max(0, factor.points)} className="enterprise-factor-track" role="progressbar"><i style={{ width: `${width}%` }} /></div>
                        <small>{factor.evidence}</small>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </article>

          <details className="enterprise-panel enterprise-raw-logs">
            <summary><span><span className="enterprise-kicker">Source telemetry</span><strong>Raw log excerpt</strong></span><span>{session.rawLogs.length} entries · expand to inspect</span></summary>
            {session.rawLogs.length === 0 ? (
              <div className="enterprise-compact-empty"><strong>No raw logs attached</strong><span>The normalized evidence above remains available.</span></div>
            ) : (
              <div className="enterprise-log-console" role="log">
                {session.rawLogs.map((entry, index) => (
                  <div key={`${entry.timestamp}-${index}`}><time dateTime={entry.timestamp}>{entry.timestamp}</time><span>{entry.source}</span><code>{entry.message}</code></div>
                ))}
              </div>
            )}
          </details>
        </div>

        <aside className="enterprise-response-panel enterprise-panel">
          <div className="enterprise-response-header">
            <span className="enterprise-response-icon"><EnterpriseIcon name="shield" size={21} /></span>
            <div><span className="enterprise-kicker">Risk-based control</span><h2>Respond to this session</h2></div>
          </div>
          <p className="enterprise-response-guidance">Choose the least disruptive control that addresses the observed behavior. Each response records the actor, time, and enforcement status.</p>

          {session.response && (
            <div className="enterprise-current-response">
              <span>Latest control-plane action</span>
              <strong>{session.response.action.replaceAll("_", " ")}</strong>
              <small>{session.response.actor} · {formatCompactDate(session.response.actedAt)}</small>
              {session.response.reference && <code>{session.response.reference}</code>}
            </div>
          )}

          <label className="enterprise-response-note">
            <span>Analyst note <small>optional</small></span>
            <textarea maxLength={500} onChange={(event) => setNote(event.target.value)} placeholder="Reason, corroborating evidence, or ticket reference…" rows={4} value={note} />
            <small>{note.length}/500 · actor: {analystName}</small>
          </label>

          <div className="enterprise-response-actions">
            {actionDetails.map((item) => (
              <button
                className={`enterprise-response-action enterprise-action-${item.action.toLowerCase().replaceAll("_", "-")}`}
                disabled={pendingAction !== null}
                key={item.action}
                onClick={() => void submitResponse(item.action)}
                type="button"
              >
                <span><EnterpriseIcon name={item.icon} /></span>
                <span><strong>{pendingAction === item.action ? "Applying…" : item.label}</strong><small>{item.description}</small></span>
              </button>
            ))}
          </div>

          {responseError && <div className="enterprise-response-feedback is-error" role="alert"><EnterpriseIcon name="alert" size={16} />{responseError}</div>}
          {responseMessage && <div className="enterprise-response-feedback is-success" role="status"><EnterpriseIcon name="check" size={16} />{responseMessage}</div>}

          <footer className="enterprise-response-proof">
            <span><EnterpriseIcon name="shield" size={14} /> Policy evaluation</span>
            <strong>Decision → enforcement status → audit record</strong>
          </footer>
        </aside>
      </div>
    </section>
  );
}
