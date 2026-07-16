import { EnterpriseIcon } from "./EnterpriseIcon";
import { formatCompactDate, riskLabel, riskTier } from "./risk";
import "./enterprise.css";

export type TriageStatus = "NORMAL" | "FLAGGED" | "ACTIONED" | "ACTIVE";
export type SessionSortColumn = "riskScore" | "startedAt" | "userId" | "resource" | "status";
export type SortDirection = "asc" | "desc";

export interface TriageSession {
  sessionId: string;
  userId: string;
  role: string;
  startedAt: string;
  resource: string;
  sourceIp?: string;
  riskScore: number;
  status: TriageStatus;
  decision?: "ALLOW" | "STEP_UP_AUTH" | "BLOCK";
}

export interface SessionFilters {
  user: string;
  resource: string;
  riskMin: number;
  dateFrom: string;
  dateTo: string;
}

export interface SessionSort {
  column: SessionSortColumn;
  direction: SortDirection;
}

export interface SessionTriageProps {
  items: TriageSession[];
  total: number;
  page: number;
  pageSize: number;
  filters: SessionFilters;
  sort: SessionSort;
  loading?: boolean;
  error?: string | null;
  onFiltersChange: (filters: SessionFilters) => void;
  onApplyFilters?: () => void | Promise<void>;
  onClearFilters?: () => void;
  onSortChange: (sort: SessionSort) => void;
  onPageChange: (page: number) => void;
  onOpenSession: (sessionId: string) => void;
  onRetry?: () => void | Promise<void>;
}

const columns: ReadonlyArray<{ key: SessionSortColumn; label: string }> = [
  { key: "userId", label: "Identity / role" },
  { key: "startedAt", label: "Session start" },
  { key: "resource", label: "Protected resource" },
  { key: "riskScore", label: "Risk score" },
  { key: "status", label: "Status" },
];

export function defaultSessionFilters(): SessionFilters {
  return { user: "", resource: "", riskMin: 0, dateFrom: "", dateTo: "" };
}

export function SessionTriage({
  items,
  total,
  page,
  pageSize,
  filters,
  sort,
  loading = false,
  error = null,
  onFiltersChange,
  onApplyFilters,
  onClearFilters,
  onSortChange,
  onPageChange,
  onOpenSession,
  onRetry,
}: SessionTriageProps) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
  const safePage = Math.max(1, Math.min(page, totalPages));
  const firstItem = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const lastItem = Math.min(total, safePage * pageSize);

  const updateFilter = <Key extends keyof SessionFilters>(key: Key, value: SessionFilters[Key]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const toggleSort = (column: SessionSortColumn) => {
    onSortChange({
      column,
      direction: sort.column === column && sort.direction === "desc" ? "asc" : "desc",
    });
  };

  return (
    <section aria-labelledby="session-triage-title" className="enterprise-view enterprise-session-triage">
      <header className="enterprise-view-header">
        <div>
          <span className="enterprise-eyebrow"><i className="enterprise-live-dot" /> LATEST ASSESSMENTS</span>
          <h1 id="session-triage-title">Privileged sessions</h1>
          <p>Review assessed privileged sessions and open high-risk records for investigation.</p>
        </div>
        <div className="enterprise-session-count"><strong>{total.toLocaleString()}</strong><span>sessions in scope</span></div>
      </header>

      <form
        className="enterprise-filter-bar"
        onSubmit={(event) => {
          event.preventDefault();
          void onApplyFilters?.();
        }}
      >
        <label className="enterprise-filter-search">
          <span>User or session</span>
          <span className="enterprise-input-with-icon"><EnterpriseIcon name="search" size={16} /><input aria-label="Filter by user or session" onChange={(event) => updateFilter("user", event.target.value)} placeholder="e.g. admin-07" type="search" value={filters.user} /></span>
        </label>
        <label>
          <span>Protected resource</span>
          <input onChange={(event) => updateFilter("resource", event.target.value)} placeholder="Core banking, SWIFT…" type="text" value={filters.resource} />
        </label>
        <label>
          <span>Minimum risk score</span>
          <select onChange={(event) => updateFilter("riskMin", Number(event.target.value))} value={filters.riskMin}>
            <option value={0}>Any score</option>
            <option value={40}>40 · Elevated</option>
            <option value={70}>70 · Critical</option>
            <option value={85}>85 · Severe</option>
          </select>
        </label>
        <label>
          <span>From</span>
          <input onChange={(event) => updateFilter("dateFrom", event.target.value)} type="date" value={filters.dateFrom} />
        </label>
        <label>
          <span>To</span>
          <input onChange={(event) => updateFilter("dateTo", event.target.value)} type="date" value={filters.dateTo} />
        </label>
        <div className="enterprise-filter-actions">
          {onClearFilters && <button className="enterprise-button enterprise-button-quiet" onClick={onClearFilters} type="button">Clear</button>}
          <button className="enterprise-button enterprise-button-primary" disabled={loading} type="submit">Apply filters</button>
        </div>
      </form>

      {error && (
        <div className="enterprise-inline-alert enterprise-inline-alert-error" role="alert">
          <EnterpriseIcon name="alert" size={16} />
          <span><strong>Session query failed.</strong> {error}</span>
          {onRetry && <button className="enterprise-text-button" onClick={() => void onRetry()} type="button">Retry</button>}
        </div>
      )}

      <article aria-busy={loading} className="enterprise-panel enterprise-table-panel">
        <div className="enterprise-table-toolbar">
          <div><span className="enterprise-kicker">Analyst queue</span><h2>Risk-ranked access activity</h2></div>
          <span className="enterprise-table-range">{firstItem.toLocaleString()}–{lastItem.toLocaleString()} of {total.toLocaleString()}</span>
        </div>
        <div className="enterprise-table-scroll">
          <table className="enterprise-data-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key} scope="col">
                    <button
                      aria-label={`Sort by ${column.label}${sort.column === column.key ? `, currently ${sort.direction}ending` : ""}`}
                      className={sort.column === column.key ? "is-sorted" : undefined}
                      onClick={() => toggleSort(column.key)}
                      type="button"
                    >
                      {column.label}<span aria-hidden="true">{sort.column === column.key ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span>
                    </button>
                  </th>
                ))}
                <th aria-label="Open investigation" scope="col" />
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 && Array.from({ length: 6 }, (_, index) => (
                <tr className="enterprise-loading-row" key={index}><td colSpan={6}><span className="enterprise-skeleton" /></td></tr>
              ))}
              {!loading && !error && items.length === 0 && (
                <tr><td colSpan={6}><div className="enterprise-table-empty"><EnterpriseIcon name="search" size={22} /><strong>No sessions match these filters</strong><span>Broaden the date or risk range to continue triage.</span></div></td></tr>
              )}
              {items.map((session) => {
                const tier = riskTier(session.riskScore);
                return (
                  <tr className="enterprise-clickable-row" key={session.sessionId} onClick={() => onOpenSession(session.sessionId)}>
                    <td><span className="enterprise-table-identity"><strong>{session.userId}</strong><small>{session.role} · {session.sessionId}</small></span></td>
                    <td><time dateTime={session.startedAt}>{formatCompactDate(session.startedAt)}</time>{session.sourceIp && <small className="enterprise-table-secondary">{session.sourceIp}</small>}</td>
                    <td><strong>{session.resource}</strong></td>
                    <td><span className={`enterprise-table-risk enterprise-risk-${tier}`}><strong>{Math.round(session.riskScore)}</strong><small>{riskLabel(session.riskScore)}</small></span></td>
                    <td><span className={`enterprise-status-pill enterprise-status-${session.status.toLowerCase()}`}>{session.status}</span>{session.decision && <small className="enterprise-table-secondary">{session.decision.replaceAll("_", " ")}</small>}</td>
                    <td><button aria-label={`Investigate session ${session.sessionId}`} className="enterprise-row-action" onClick={(event) => { event.stopPropagation(); onOpenSession(session.sessionId); }} type="button"><EnterpriseIcon name="arrow" size={17} /></button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <footer className="enterprise-pagination">
          <span>Page {safePage} of {totalPages}</span>
          <div>
            <button className="enterprise-button enterprise-button-secondary" disabled={safePage <= 1 || loading} onClick={() => onPageChange(safePage - 1)} type="button">Previous</button>
            <button className="enterprise-button enterprise-button-secondary" disabled={safePage >= totalPages || loading} onClick={() => onPageChange(safePage + 1)} type="button">Next</button>
          </div>
        </footer>
      </article>
    </section>
  );
}
