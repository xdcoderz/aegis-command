import { EnterpriseIcon } from "./EnterpriseIcon";
import { clampRisk, formatCompactDate, riskLabel, riskTier } from "./risk";
import "./enterprise.css";

export type SessionOperationalStatus = "NORMAL" | "FLAGGED" | "ACTIONED" | "ACTIVE";

export interface CommandCenterSession {
  sessionId: string;
  userId: string;
  role: string;
  resource: string;
  occurredAt: string;
  riskScore: number;
  status: SessionOperationalStatus;
}

export interface CommandCenterData {
  activeFlags: number;
  sessionsMonitored24h: number;
  averageRiskScore: number;
  escalationsToday: number;
  pqcVault: {
    ready: boolean;
    algorithm: string;
    encryptedItems: number;
  };
  riskTrend: number[];
  topRiskySessions: CommandCenterSession[];
}

export interface CommandCenterProps {
  data: CommandCenterData | null;
  loading?: boolean;
  error?: string | null;
  lastUpdated?: string | null;
  onOpenSession: (sessionId: string) => void;
  onRefresh?: () => void | Promise<void>;
  onOpenVault?: () => void;
  onOpenSessions?: () => void;
}

function Sparkline({ points }: { points: number[] }) {
  const safe = points.map(clampRisk);
  const width = 240;
  const height = 70;
  const padding = 5;
  const denominator = Math.max(1, safe.length - 1);
  const plotted = safe.map((value, index) => ({
    x: padding + (index / denominator) * (width - padding * 2),
    y: height - padding - (value / 100) * (height - padding * 2),
  }));
  const polyline = plotted.map(({ x, y }) => `${x},${y}`).join(" ");
  const fill = plotted.length > 1
    ? `${plotted[0]?.x ?? padding},${height - padding} ${polyline} ${plotted.at(-1)?.x ?? width - padding},${height - padding}`
    : "";

  if (safe.length === 0) {
    return <div className="enterprise-sparkline-empty">Trend begins as sessions are assessed</div>;
  }

  return (
    <svg
      aria-label={`Risk trend, latest score ${Math.round(safe.at(-1) ?? 0)} out of 100`}
      className="enterprise-sparkline"
      preserveAspectRatio="none"
      role="img"
      viewBox={`0 0 ${width} ${height}`}
    >
      <line className="enterprise-sparkline-guide" x1="0" x2={width} y1="28" y2="28" />
      <line className="enterprise-sparkline-guide" x1="0" x2={width} y1="46" y2="46" />
      {fill && <polygon className="enterprise-sparkline-fill" points={fill} />}
      {polyline && <polyline className="enterprise-sparkline-line" points={polyline} />}
      {plotted.at(-1) && (
        <circle
          className="enterprise-sparkline-point"
          cx={plotted.at(-1)?.x}
          cy={plotted.at(-1)?.y}
          r="3"
        />
      )}
    </svg>
  );
}

function CommandCenterSkeleton() {
  return (
    <div aria-label="Loading command center" className="enterprise-loading-grid" role="status">
      {Array.from({ length: 4 }, (_, index) => (
        <span className="enterprise-skeleton enterprise-skeleton-card" key={index} />
      ))}
      <span className="enterprise-skeleton enterprise-skeleton-panel" />
      <span className="enterprise-skeleton enterprise-skeleton-panel" />
    </div>
  );
}

export function CommandCenter({
  data,
  loading = false,
  error = null,
  lastUpdated = null,
  onOpenSession,
  onRefresh,
  onOpenVault,
  onOpenSessions,
}: CommandCenterProps) {
  if (loading && !data) return <CommandCenterSkeleton />;

  if (error && !data) {
    return (
      <section className="enterprise-state enterprise-state-error" role="alert">
        <span className="enterprise-state-icon"><EnterpriseIcon name="alert" size={22} /></span>
        <div><strong>Command center unavailable</strong><p>{error}</p></div>
        {onRefresh && <button className="enterprise-button enterprise-button-secondary" onClick={() => void onRefresh()} type="button">Retry</button>}
      </section>
    );
  }

  if (!data) {
    return (
      <section className="enterprise-state">
        <span className="enterprise-state-icon"><EnterpriseIcon name="activity" size={22} /></span>
        <div><strong>No telemetry yet</strong><p>Risk posture will appear when the first privileged session is assessed.</p></div>
      </section>
    );
  }

  const trendLatest = data.riskTrend.at(-1) ?? data.averageRiskScore;
  const trendPrevious = data.riskTrend.at(-2) ?? trendLatest;
  const trendDelta = trendLatest - trendPrevious;

  return (
    <section aria-labelledby="command-center-title" className="enterprise-view enterprise-command-center">
      <header className="enterprise-view-header">
        <div>
          <span className="enterprise-eyebrow"><i className="enterprise-live-dot" /> OPERATIONAL RISK SUMMARY</span>
          <h1 id="command-center-title">Command center</h1>
          <p>Review current session risk, response activity, and vault status.</p>
        </div>
        <div className="enterprise-header-actions">
          {lastUpdated && <span className="enterprise-updated"><EnterpriseIcon name="clock" size={15} /> Updated {formatCompactDate(lastUpdated)}</span>}
          {onRefresh && (
            <button aria-label="Refresh command center" className="enterprise-icon-button" disabled={loading} onClick={() => void onRefresh()} type="button">
              <EnterpriseIcon name="refresh" />
            </button>
          )}
        </div>
      </header>

      {error && <div className="enterprise-inline-alert" role="status"><EnterpriseIcon name="alert" size={15} /> Showing cached data. {error}</div>}

      <div className="enterprise-metric-grid">
        <article className={`enterprise-metric-card enterprise-metric-${data.activeFlags > 0 ? "danger" : "neutral"}`}>
          <div className="enterprise-metric-label"><EnterpriseIcon name="alert" /> Active flags</div>
          <strong>{data.activeFlags.toLocaleString()}</strong>
          <span>{data.activeFlags === 1 ? "session needs" : "sessions need"} analyst review</span>
        </article>
        <article className="enterprise-metric-card">
          <div className="enterprise-metric-label"><EnterpriseIcon name="activity" /> Sessions assessed</div>
          <strong>{data.sessionsMonitored24h.toLocaleString()}</strong>
          <span>Privileged sessions assessed · last 24 hours</span>
        </article>
        <article className={`enterprise-metric-card enterprise-metric-${riskTier(data.averageRiskScore)}`}>
          <div className="enterprise-metric-label"><EnterpriseIcon name="shield" /> Average risk</div>
          <strong>{Math.round(data.averageRiskScore)}<small>/100</small></strong>
          <span>{riskLabel(data.averageRiskScore)} · average across assessed sessions</span>
        </article>
        <button className={`enterprise-metric-card enterprise-vault-card ${data.pqcVault.ready ? "is-ready" : "is-degraded"}`} onClick={onOpenVault} type="button">
          <div className="enterprise-metric-label"><EnterpriseIcon name="key" /> PQC vault</div>
          <strong>{data.pqcVault.ready ? "PQC active" : "Compatibility mode"}</strong>
          <span>{data.pqcVault.algorithm} · {data.pqcVault.encryptedItems.toLocaleString()} encrypted {data.pqcVault.encryptedItems === 1 ? "envelope" : "envelopes"}</span>
        </button>
      </div>

      <div className="enterprise-command-grid">
        <article className="enterprise-panel enterprise-risk-queue">
          <div className="enterprise-panel-header">
            <div><span className="enterprise-kicker">Priority queue</span><h2>Highest-risk sessions</h2></div>
            {onOpenSessions && <button className="enterprise-text-button" onClick={onOpenSessions} type="button">View all <EnterpriseIcon name="arrow" size={15} /></button>}
          </div>

          {data.topRiskySessions.length === 0 ? (
            <div className="enterprise-compact-empty"><EnterpriseIcon name="check" /><strong>No high-risk sessions</strong><span>Current monitored activity is within policy.</span></div>
          ) : (
            <ol className="enterprise-ranked-list">
              {data.topRiskySessions.map((session, index) => {
                const tier = riskTier(session.riskScore);
                return (
                  <li key={session.sessionId}>
                    <button className="enterprise-risk-row" onClick={() => onOpenSession(session.sessionId)} type="button">
                      <span className="enterprise-rank">{String(index + 1).padStart(2, "0")}</span>
                      <span className="enterprise-risk-identity"><strong>{session.userId}</strong><small>{session.role} · {session.resource}</small></span>
                      <span className={`enterprise-status-pill enterprise-status-${session.status.toLowerCase()}`}>{session.status}</span>
                      <span className="enterprise-risk-time">{formatCompactDate(session.occurredAt)}</span>
                      <span className={`enterprise-risk-score enterprise-risk-${tier}`} aria-label={`${riskLabel(session.riskScore)} risk, ${Math.round(session.riskScore)} out of 100`}><small>{riskLabel(session.riskScore)}</small>{Math.round(session.riskScore)}</span>
                      <EnterpriseIcon name="arrow" size={16} />
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </article>

        <aside className="enterprise-command-aside">
          <article className="enterprise-panel enterprise-trend-card">
            <div className="enterprise-panel-header enterprise-panel-header-compact">
              <div><span className="enterprise-kicker">Last 24 hours</span><h2>Risk trend</h2></div>
              <span className={`enterprise-trend-delta ${trendDelta > 0 ? "is-up" : "is-down"}`}>{trendDelta > 0 ? "+" : ""}{Math.round(trendDelta)} pts</span>
            </div>
            <Sparkline points={data.riskTrend} />
            <div className="enterprise-chart-legend"><span>00:00</span><strong>Average session risk by time window</strong><span>Now</span></div>
          </article>
          <article className="enterprise-panel enterprise-escalation-card">
            <div className="enterprise-escalation-icon"><EnterpriseIcon name="shield" size={22} /></div>
            <div><span className="enterprise-kicker">Access responses</span><strong>{data.escalationsToday.toLocaleString()}</strong><p>Step-up or block responses recorded today</p></div>
          </article>
        </aside>
      </div>
    </section>
  );
}
