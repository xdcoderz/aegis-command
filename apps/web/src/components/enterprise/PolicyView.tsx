import { useEffect, useState } from "react";

export interface RiskThresholdPolicy {
  stepUpThreshold: number;
  blockThreshold: number;
  version?: string;
  updatedAt?: string;
}

export interface PolicyViewProps {
  policy: RiskThresholdPolicy;
  readOnly?: boolean;
  onSave: (policy: Pick<RiskThresholdPolicy, "stepUpThreshold" | "blockThreshold">) => Promise<RiskThresholdPolicy | void>;
}

function normalizedScore(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function PolicyView({ policy, readOnly = false, onSave }: PolicyViewProps) {
  const [stepUpThreshold, setStepUpThreshold] = useState(policy.stepUpThreshold);
  const [blockThreshold, setBlockThreshold] = useState(policy.blockThreshold);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStepUpThreshold(policy.stepUpThreshold);
    setBlockThreshold(policy.blockThreshold);
  }, [policy.blockThreshold, policy.stepUpThreshold]);

  const isValid = stepUpThreshold >= 1 && blockThreshold <= 100 && stepUpThreshold < blockThreshold;
  const changed = stepUpThreshold !== policy.stepUpThreshold || blockThreshold !== policy.blockThreshold;

  async function savePolicy() {
    if (!isValid) {
      setError("The step-up threshold must be lower than the block threshold.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await onSave({ stepUpThreshold, blockThreshold });
      setMessage("Policy saved. New assessments will use these thresholds.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The policy could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="enterprise-view policy-view" aria-labelledby="policy-title">
      <header className="enterprise-page-header">
        <div>
          <span className="enterprise-eyebrow">RISK-BASED ACCESS CONTROL</span>
          <h1 id="policy-title">Policy thresholds</h1>
          <p>Set the score thresholds used for step-up authentication and session blocking.</p>
        </div>
        {policy.version && <div className="policy-version"><span>Active policy</span><strong>{policy.version}</strong></div>}
      </header>

      <section className="enterprise-panel policy-editor" aria-labelledby="decision-boundaries-title">
        {readOnly && <p className="enterprise-access-note">Policy is read-only for SOC analysts. Switch to <strong>Security admin</strong> in the top bar to publish threshold changes.</p>}
        <div className="enterprise-panel-heading">
          <div>
            <span className="section-index">CURRENT POLICY</span>
            <h2 id="decision-boundaries-title">Decision boundaries</h2>
            <p>Set when sessions require reauthentication and when a block response is submitted.</p>
          </div>
          {policy.updatedAt && <small>Last updated {new Date(policy.updatedAt).toLocaleString()}</small>}
        </div>

        <div className="policy-score-band" aria-label="Current risk outcome ranges">
          <span className="policy-band-allow" style={{ width: `${stepUpThreshold}%` }}>Allow</span>
          <span className="policy-band-step-up" style={{ width: `${blockThreshold - stepUpThreshold}%` }}>Step-up</span>
          <span className="policy-band-block" style={{ width: `${100 - blockThreshold}%` }}>Block</span>
        </div>
        <div className="policy-score-axis" aria-hidden="true"><span>0</span><span>Risk score</span><span>100</span></div>

        <div className="policy-slider-stack">
          <div className="policy-slider-field">
            <div className="policy-slider-heading">
              <label htmlFor="step-up-threshold">Step-up authentication starts at</label>
              <output htmlFor="step-up-threshold">{stepUpThreshold}</output>
            </div>
            <input
              id="step-up-threshold"
              type="range"
              min="1"
              max="99"
              value={stepUpThreshold}
              onChange={(event) => { setStepUpThreshold(normalizedScore(Number(event.target.value))); setMessage(null); }}
              disabled={saving || readOnly}
            />
            <p>Sessions at or above this score receive a STEP_UP decision for the configured identity control.</p>
          </div>

          <div className="policy-slider-field">
            <div className="policy-slider-heading">
              <label htmlFor="block-threshold">Automatic block starts at</label>
              <output htmlFor="block-threshold">{blockThreshold}</output>
            </div>
            <input
              id="block-threshold"
              type="range"
              min="2"
              max="100"
              value={blockThreshold}
              onChange={(event) => { setBlockThreshold(normalizedScore(Number(event.target.value))); setMessage(null); }}
              disabled={saving || readOnly}
            />
            <p>Sessions at or above this score receive a BLOCK decision and are submitted to the configured enforcement adapter.</p>
          </div>
        </div>

        {!isValid && <p className="enterprise-error" role="alert">Step-up must remain below block so every score maps to exactly one action.</p>}

        <div className="policy-impact-preview">
          <div><span>0–{Math.max(0, stepUpThreshold - 1)}</span><strong>Allow + monitor</strong></div>
          <div><span>{stepUpThreshold}–{Math.max(stepUpThreshold, blockThreshold - 1)}</span><strong>Step-up authentication</strong></div>
          <div><span>{blockThreshold}–100</span><strong>Block + investigate</strong></div>
        </div>

        <div className="enterprise-form-actions">
          <button className="enterprise-secondary-button" type="button" onClick={() => { setStepUpThreshold(policy.stepUpThreshold); setBlockThreshold(policy.blockThreshold); setError(null); setMessage(null); }} disabled={!changed || saving}>Reset</button>
          <button className="enterprise-primary-button" type="button" onClick={() => void savePolicy()} disabled={readOnly || !isValid || !changed || saving}>{saving ? "Saving…" : "Save policy"}</button>
        </div>
        {error && <p className="enterprise-error" role="alert">{error}</p>}
        {message && <p className="enterprise-success" role="status">✓ {message}</p>}
      </section>

      <aside className="enterprise-guidance-note">
        <strong>Policy scope</strong>
        <p>Threshold changes apply to new assessments. Existing session scores are not recalculated.</p>
      </aside>
    </main>
  );
}
