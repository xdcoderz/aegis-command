import type { CSSProperties } from "react";
import type {
  AccessDecision,
  AssessmentReview,
  ReceiptVerification,
  SessionAssessment,
} from "../types";

interface RiskPanelProps {
  assessment: SessionAssessment | null;
  actionBusy?: boolean;
  review?: AssessmentReview | null;
  receipt?: ReceiptVerification | null;
  onCreateIncident?: () => Promise<void>;
  onVerifyReceipt?: () => Promise<void>;
}

const decisionGuide: Record<AccessDecision, { title: string; copy: string }> = {
  ALLOW: {
    title: "Access can continue",
    copy: "The session matches expected behavior. Continue monitoring under the existing policy.",
  },
  STEP_UP_AUTH: {
    title: "Verify the user again",
    copy: "Aegis Command found meaningful changes. Request stronger authentication before access continues.",
  },
  BLOCK: {
    title: "Stop and investigate",
    copy: "The combined signals indicate high risk. Block this session and begin an analyst review.",
  },
};

function EmptyResult() {
  return (
    <section className="risk-panel card empty-result">
      <div className="card-step-header">
        <span className="step-chip step-muted">Step 2</span>
        <div><h3>Understand the recommendation</h3><p>Your result will appear here after the session is evaluated.</p></div>
      </div>
      <div className="empty-visual"><span className="scan-ring"><i>FS</i></span></div>
      <div className="empty-copy"><h3>Nothing to interpret yet</h3><p>Aegis Command will turn the session details into a clear score, action, and explanation.</p></div>
      <div className="what-you-get">
        <span>What you’ll get</span>
        <div><i>01</i><p><strong>A risk score</strong><small>A simple 0–100 measure of concern</small></p></div>
        <div><i>02</i><p><strong>A recommended action</strong><small>Allow, verify again, or block</small></p></div>
        <div><i>03</i><p><strong>The reasons why</strong><small>Signals ordered by their impact</small></p></div>
      </div>
    </section>
  );
}

export function RiskPanel({
  assessment,
  actionBusy = false,
  review,
  receipt,
  onCreateIncident,
  onVerifyReceipt,
}: RiskPanelProps) {
  if (!assessment) return <EmptyResult />;

  const tone = assessment.decision.toLowerCase().replaceAll("_", "-");
  const guide = decisionGuide[assessment.decision];
  const score = Math.round(assessment.risk_score);

  return (
    <section className={`risk-panel card result-card ${tone}`}>
      <div className="card-step-header result-step">
        <span className="step-chip">Step 2</span>
        <div><h3>Review the decision</h3><p>Start with the recommendation, then check the evidence.</p></div>
      </div>

      <div className="decision-hero">
        <div className="score-ring" style={{ "--score": `${score * 3.6}deg` } as CSSProperties}>
          <div><strong>{score}</strong><span>out of 100</span></div>
        </div>
        <div className="decision-copy">
          <span className={`decision-label ${tone}`}>{assessment.decision.replaceAll("_", " ")}</span>
          <h2>{guide.title}</h2>
          <p>{guide.copy}</p>
        </div>
      </div>

      <div className="next-action">
        <span>Recommended next step</span>
        <strong>{assessment.decision === "ALLOW" ? "Continue with monitoring" : assessment.decision === "STEP_UP_AUTH" ? "Trigger step-up authentication" : "Terminate access and create an incident"}</strong>
      </div>

      <div className="result-details">
        <div><span>Behavior anomaly</span><strong>{Math.round(assessment.anomaly_score * 100)}%</strong></div>
        <div><span>Policy baseline</span><strong>{assessment.baseline_scope}</strong></div>
        <div><span>Enforcement</span><strong>{assessment.enforcement_status.replaceAll("_", " ")}</strong></div>
        <div><span>Audit record</span><strong>{assessment.audit_signature ? "PQC signed" : "Decision recorded"}</strong></div>
      </div>

      <div className="factor-section">
        <div className="factor-heading"><div><h3>Why Aegis Command made this decision</h3><p>Higher-impact signals appear first.</p></div><span>{assessment.factors.length} signals</span></div>
        <div className="factor-list">
          {assessment.factors.map((factor, index) => (
            <div className="factor" key={factor.key}>
              <span className="factor-order">{String(index + 1).padStart(2, "0")}</span>
              <div className="factor-copy"><div><strong>{factor.label}</strong><b>+{factor.score.toFixed(1)}</b></div><p>{factor.evidence}</p><div className="factor-bar"><span style={{ width: `${Math.min(factor.score / 0.6, 100)}%` }} /></div></div>
            </div>
          ))}
        </div>
      </div>

      {assessment.enforcement_reference && <p className="reference-note">Control reference: <strong>{assessment.enforcement_reference}</strong></p>}

      <div className="response-console">
        <div><span className="response-kicker">RESPONSE CONTROLS</span><h3>Complete the investigation</h3><p>Persist an analyst disposition and verify the evidence without leaving this decision.</p></div>
        <div className="response-buttons">
          <button className="response-primary" disabled={actionBusy || Boolean(review)} onClick={() => void onCreateIncident?.()}>{review ? "✓ Incident created" : actionBusy ? "Working…" : "Create incident"}</button>
          <button className="response-secondary" disabled={actionBusy} onClick={() => void onVerifyReceipt?.()}>{receipt ? "✓ Receipt checked" : "Verify audit receipt"}</button>
        </div>
        {(review || receipt) && <div className="action-results">
          {review && <div><span>INCIDENT DISPOSITION</span><strong>{review.disposition}</strong><small>{review.comment}</small></div>}
          {receipt && <div><span>AUDIT VERIFICATION</span><strong>{receipt.valid ? "PQC signature valid" : "Integrity hash recalculated"}</strong><small className="hash-value">{receipt.payload_sha256}</small></div>}
        </div>}
      </div>
    </section>
  );
}
