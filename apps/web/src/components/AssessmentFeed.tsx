import type { AssessmentSummary } from "../types";

export function AssessmentFeed({ items }: { items: AssessmentSummary[] }) {
  return (
    <section className="feed card">
      <div className="section-heading">
        <div><p className="eyebrow">Decision ledger</p><h2>Recent sessions</h2></div>
        <span className="count">{items.length} records</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead><tr><th>Session</th><th>Identity</th><th>Risk</th><th>Decision</th><th>Time</th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={5} className="no-data">No decisions recorded yet.</td></tr>}
            {items.map((item) => (
              <tr key={item.assessment_id}>
                <td className="mono">{item.session_id}</td>
                <td>{item.user_id}</td>
                <td><strong>{Math.round(item.risk_score)}</strong></td>
                <td><span className={`decision ${item.decision.toLowerCase()}`}>{item.decision.replaceAll("_", " ")}</span></td>
                <td>{new Date(item.assessed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

