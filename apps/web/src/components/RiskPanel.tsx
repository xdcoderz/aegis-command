import type { SessionAssessment } from "../types";

interface RiskPanelProps {
  assessment: SessionAssessment | null;
}

export function RiskPanel({ assessment }: RiskPanelProps) {
  if (!assessment) {
    return (
      <section className="risk-panel empty-state">
        <div className="radar-ring" />
        <p>Run a privileged session to see its live risk decision.</p>
      </section>
    );
  }

  const tone = assessment.decision.toLowerCase().replaceAll("_", "-");
  return (
    <section className={`risk-panel ${tone}`}>
      <div className="risk-heading">
        <div>
          <p className="eyebrow">Live decision</p>
          <h2>{assessment.decision.replaceAll("_", " ")}</h2>
        </div>
        <div className="risk-score" aria-label={`Risk score ${assessment.risk_score}`}>
          <strong>{Math.round(assessment.risk_score)}</strong>
          <span>/100</span>
        </div>
      </div>
      <div className="risk-meter">
        <span style={{ width: `${assessment.risk_score}%` }} />
      </div>
      <div className="meta-grid">
        <div><span>Anomaly</span><strong>{Math.round(assessment.anomaly_score * 100)}%</strong></div>
        <div><span>Baseline</span><strong>{assessment.baseline_scope}</strong></div>
        <div><span>Model</span><strong>{assessment.model_version}</strong></div>
        <div><span>Audit</span><strong>{assessment.audit_signature ? "PQC signed" : "Unsigned"}</strong></div>
      </div>
      <div className="factor-list">
        {assessment.factors.map((factor) => (
          <div className="factor" key={factor.key}>
            <div><span>{factor.label}</span><strong>+{factor.score.toFixed(1)}</strong></div>
            <div className="factor-bar"><span style={{ width: `${Math.min(factor.score / 0.6, 100)}%` }} /></div>
            <small>{factor.evidence}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

