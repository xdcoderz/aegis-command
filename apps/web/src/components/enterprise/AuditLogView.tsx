import { useMemo, useState } from "react";

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  sessionId: string;
  action: string;
  actor: string;
  riskScore: number;
  evidenceStatus?: "RECORDED" | "VERIFIED" | "PENDING" | "FAILED";
}

export interface AuditLogViewProps {
  entries: AuditLogEntry[];
  loading?: boolean;
  onOpenSession?: (sessionId: string) => void;
  onExportCsv?: (entries: AuditLogEntry[]) => void | Promise<void>;
  onExportPdf?: (entries: AuditLogEntry[]) => void | Promise<void>;
}

type ExportFormat = "csv" | "pdf" | null;

function riskTone(score: number) {
  if (score >= 80) return "critical";
  if (score >= 55) return "elevated";
  return "normal";
}

export function AuditLogView({ entries, loading = false, onOpenSession, onExportCsv, onExportPdf }: AuditLogViewProps) {
  const [query, setQuery] = useState("");
  const [action, setAction] = useState("ALL");
  const [date, setDate] = useState("");
  const [exporting, setExporting] = useState<ExportFormat>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const actions = useMemo(() => Array.from(new Set(entries.map((entry) => entry.action))).sort(), [entries]);
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return entries
      .filter((entry) => {
        const matchesQuery = !normalizedQuery || `${entry.sessionId} ${entry.actor} ${entry.action}`.toLocaleLowerCase().includes(normalizedQuery);
        const matchesAction = action === "ALL" || entry.action === action;
        const matchesDate = !date || entry.timestamp.slice(0, 10) === date;
        return matchesQuery && matchesAction && matchesDate;
      })
      .sort((left, right) => Date.parse(right.timestamp) - Date.parse(left.timestamp));
  }, [action, date, entries, query]);

  async function exportLog(format: Exclude<ExportFormat, null>) {
    const handler = format === "csv" ? onExportCsv : onExportPdf;
    if (!handler) return;
    setExporting(format);
    setExportError(null);
    try {
      await handler(filtered);
    } catch (caught) {
      setExportError(caught instanceof Error ? caught.message : `The ${format.toUpperCase()} export failed.`);
    } finally {
      setExporting(null);
    }
  }

  return (
    <main className="enterprise-view audit-log-view" aria-labelledby="audit-log-title">
      <header className="enterprise-page-header">
        <div>
          <span className="enterprise-eyebrow">DECISION AND RESPONSE RECORDS</span>
          <h1 id="audit-log-title">Audit log</h1>
          <p>Review recorded risk decisions and analyst responses with their enforcement status.</p>
        </div>
        <div className="audit-export-actions" aria-label="Export audit log">
          <button className="enterprise-secondary-button" type="button" disabled={!onExportCsv || exporting !== null || filtered.length === 0} onClick={() => void exportLog("csv")}>{exporting === "csv" ? "Exporting…" : "Export CSV"}</button>
          <button className="enterprise-secondary-button" type="button" disabled={!onExportPdf || exporting !== null || filtered.length === 0} onClick={() => void exportLog("pdf")}>{exporting === "pdf" ? "Preparing…" : "Print / save PDF"}</button>
        </div>
      </header>

      <section className="enterprise-panel audit-log-panel">
        <div className="audit-filter-bar" aria-label="Audit log filters">
          <label className="enterprise-search-field">
            <span className="sr-only">Search session, actor, or action</span>
            <span aria-hidden="true">⌕</span>
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search session, actor, action…" />
          </label>
          <label className="enterprise-select-field">
            <span>Action</span>
            <select value={action} onChange={(event) => setAction(event.target.value)}>
              <option value="ALL">All actions</option>
              {actions.map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="enterprise-date-field">
            <span>Date</span>
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </label>
          <button className="text-button" type="button" onClick={() => { setQuery(""); setAction("ALL"); setDate(""); }} disabled={!query && action === "ALL" && !date}>Clear filters</button>
          <span className="filter-result-count">{filtered.length} {filtered.length === 1 ? "event" : "events"}</span>
        </div>

        <div className="enterprise-table-scroll">
          <table className="enterprise-table audit-table">
            <thead><tr><th scope="col">Timestamp</th><th scope="col">Session</th><th scope="col">Action</th><th scope="col">Actor</th><th scope="col">Risk</th><th scope="col">Record status</th></tr></thead>
            <tbody>
              {loading && <tr><td colSpan={6} className="table-status-cell">Loading audit records…</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan={6} className="table-status-cell">No events match the active filters.</td></tr>}
              {!loading && filtered.map((entry) => (
                <tr key={entry.id}>
                  <td><time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time></td>
                  <td>{onOpenSession ? <button className="table-link-button" type="button" onClick={() => onOpenSession(entry.sessionId)}>{entry.sessionId}</button> : <span className="table-mono">{entry.sessionId}</span>}</td>
                  <td><span className="audit-action-chip">{entry.action.replaceAll("_", " ")}</span></td>
                  <td>{entry.actor}</td>
                  <td><span className={`audit-risk-score ${riskTone(entry.riskScore)}`}>{Math.round(entry.riskScore)}</span></td>
                  <td><span className={`evidence-status ${(entry.evidenceStatus ?? "PENDING").toLowerCase()}`}><i aria-hidden="true" />{entry.evidenceStatus ?? "PENDING"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {exportError && <p className="enterprise-error" role="alert">{exportError}</p>}
      </section>
    </main>
  );
}
