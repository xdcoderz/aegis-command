import type { AssessmentSummary } from "../types";

export function AssessmentFeed({ items, onOpen }: {
  items: AssessmentSummary[];
  onOpen?: (assessmentId: string) => Promise<void>;
}) {
  return (
    <div className="history-card card">
      <div className="history-toolbar"><div><strong>Recent privileged sessions</strong><span>Newest decisions appear first</span></div><span className="record-count">{items.length} {items.length === 1 ? "record" : "records"}</span></div>
      <div className="table-scroll">
        <table>
          <thead><tr><th>Session</th><th>Identity</th><th>Risk</th><th>Decision</th><th>Enforcement</th><th>Assessed</th>{onOpen && <th />}</tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={onOpen ? 7 : 6} className="no-data"><span>↗</span><strong>No decisions recorded yet</strong><small>Complete an assessment to create the first record.</small></td></tr>}
            {items.map((item) => (
              <tr key={item.assessment_id}>
                <td><strong className="mono">{item.session_id}</strong></td>
                <td>{item.user_id}</td>
                <td><span className="risk-number">{Math.round(item.risk_score)}</span><small>/100</small></td>
                <td><span className={`decision ${item.decision.toLowerCase().replaceAll("_", "-")}`}>{item.decision.replaceAll("_", " ")}</span></td>
                <td><span className="enforcement-state"><i className={item.enforcement_status === "FAILED" ? "failed" : ""} />{item.enforcement_status.replaceAll("_", " ")}</span></td>
                <td>{new Date(item.assessed_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</td>
                {onOpen && <td><button className="open-record" onClick={() => void onOpen(item.assessment_id)}>Open →</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
