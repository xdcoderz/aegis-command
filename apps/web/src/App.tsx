import { useEffect, useState } from "react";
import { AssessmentFeed } from "./components/AssessmentFeed";
import { RiskPanel } from "./components/RiskPanel";
import { SessionComposer } from "./components/SessionComposer";
import { api } from "./lib/api";
import type { AssessmentSummary, Readiness, SessionAssessment, SessionEvent } from "./types";

export default function App() {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [recent, setRecent] = useState<AssessmentSummary[]>([]);
  const [assessment, setAssessment] = useState<SessionAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.readiness(), api.recent()])
      .then(([health, records]) => { setReadiness(health); setRecent(records); })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "API unavailable"));
  }, []);

  async function assess(event: SessionEvent) {
    setBusy(true);
    setError(null);
    try {
      const result = await api.assess(event);
      setAssessment(result);
      setRecent(await api.recent());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Assessment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <aside>
        <div className="brand"><span className="brand-mark">FS</span><div><strong>FinSpark</strong><small>Sentinel</small></div></div>
        <nav><a className="selected" href="#overview">Overview</a><a href="#sessions">Sessions</a><a href="#policies">Policies</a><a href="#vault">PQC Vault</a></nav>
        <div className="system-status">
          <p className="eyebrow">System posture</p>
          <div><span className={readiness ? "status-dot online" : "status-dot"} />{readiness?.status ?? "Connecting"}</div>
          <small>{readiness?.pqc.available ? `${readiness.pqc.signature_algorithm} active` : "PQC unavailable"}</small>
        </div>
      </aside>
      <main>
        <header><div><p className="eyebrow">Privileged access intelligence</p><h1>Risk operations</h1></div><div className="environment">BANK-SANDBOX · LIVE</div></header>
        {error && <div className="error-banner">{error}</div>}
        <div className="hero-grid" id="overview"><SessionComposer busy={busy} onSubmit={assess} /><RiskPanel assessment={assessment} /></div>
        <AssessmentFeed items={recent} />
      </main>
    </div>
  );
}

