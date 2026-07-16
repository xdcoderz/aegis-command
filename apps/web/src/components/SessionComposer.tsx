import { useState, type FormEvent } from "react";
import type { SessionEvent } from "../types";

interface Props {
  busy: boolean;
  onSubmit: (event: SessionEvent) => Promise<void>;
}

const maliciousPreset: SessionEvent = {
  session_id: "demo-attack-01",
  user_id: "admin-00",
  role: "database-admin",
  occurred_at: "2026-03-01T02:15:00.000Z",
  source_ip: "198.51.100.77",
  device_id: "unmanaged-laptop",
  resource: "core-banking-master",
  resource_sensitivity: 1,
  commands: ["mimikatz credential dump", "disable audit", "scp customer.dump remote"],
  session_duration_minutes: 2,
  privilege_level: 5,
  privilege_escalated: true,
  failed_auth_attempts: 4,
  bytes_transferred: 50_000_000,
};

const normalPreset: SessionEvent = {
  session_id: "demo-normal-01",
  user_id: "admin-00",
  role: "database-admin",
  occurred_at: "2026-03-01T11:15:00.000Z",
  source_ip: "10.20.0.15",
  device_id: "managed-00",
  resource: "customer-db",
  resource_sensitivity: 0.75,
  commands: ["select health", "show replication", "backup verify"],
  session_duration_minutes: 31,
  privilege_level: 3,
  privilege_escalated: false,
  failed_auth_attempts: 0,
  bytes_transferred: 24_000,
};

export function SessionComposer({ busy, onSubmit }: Props) {
  const [event, setEvent] = useState<SessionEvent>(maliciousPreset);
  const [preset, setPreset] = useState<"normal" | "anomalous">("anomalous");

  function choosePreset(next: "normal" | "anomalous") {
    setPreset(next);
    setEvent(next === "normal" ? normalPreset : maliciousPreset);
  }

  async function submit(formEvent: FormEvent) {
    formEvent.preventDefault();
    await onSubmit({
      ...event,
      event_id: crypto.randomUUID(),
      session_id: `${event.session_id.replace(/-\d+$/, "")}-${Date.now()}`,
    });
  }

  return (
    <section className="composer card">
      <div className="card-step-header">
        <span className="step-chip">Step 1</span>
        <div><h3>Tell us about the session</h3><p>Use a ready-made example or enter the access context you want to check.</p></div>
      </div>

      <div className="preset-block">
        <div className="field-title"><span>Choose a starting point</span><small>You can edit every value below</small></div>
        <div className="preset-switch" role="group" aria-label="Session preset">
          <button type="button" className={preset === "normal" ? "active" : ""} onClick={() => choosePreset("normal")}>
            <span className="preset-icon normal">✓</span><span><strong>Expected activity</strong><small>Known device, routine commands</small></span>
          </button>
          <button type="button" className={preset === "anomalous" ? "active" : ""} onClick={() => choosePreset("anomalous")}>
            <span className="preset-icon anomalous">!</span><span><strong>Suspicious activity</strong><small>Unknown device, risky commands</small></span>
          </button>
        </div>
      </div>

      <form onSubmit={submit}>
        <div className="form-section-label"><span>Access context</span><small>Who is accessing what, and from where?</small></div>
        <div className="form-grid">
          <label className="field"><span>User identity</span><input required value={event.user_id} onChange={(e) => setEvent({ ...event, user_id: e.target.value })} /><small>The employee or service account</small></label>
          <label className="field"><span>Privileged role</span><input required value={event.role} onChange={(e) => setEvent({ ...event, role: e.target.value })} /><small>The role active in this session</small></label>
          <label className="field"><span>Protected resource</span><input required value={event.resource} onChange={(e) => setEvent({ ...event, resource: e.target.value })} /><small>The system or data being accessed</small></label>
          <label className="field"><span>Source IP address</span><input required value={event.source_ip} onChange={(e) => setEvent({ ...event, source_ip: e.target.value })} /><small>Where the session originated</small></label>
        </div>

        <label className="field command-field"><span>Observed commands</span><textarea required rows={4} value={event.commands.join("\n")} onChange={(e) => setEvent({ ...event, commands: e.target.value.split("\n").filter(Boolean) })} /><small>Enter one command per line. FinSpark treats this as telemetry, never as executable input.</small></label>

        <details className="advanced-details">
          <summary><span><strong>Review advanced signals</strong><small>Optional details improve the recommendation</small></span><i>+</i></summary>
          <div className="advanced-grid">
            <label className="field"><span>Resource sensitivity <b>{Math.round(event.resource_sensitivity * 100)}%</b></span><input type="range" min="0" max="1" step="0.05" value={event.resource_sensitivity} onChange={(e) => setEvent({ ...event, resource_sensitivity: Number(e.target.value) })} /></label>
            <label className="field"><span>Privilege level</span><input type="number" min="1" max="5" value={event.privilege_level} onChange={(e) => setEvent({ ...event, privilege_level: Number(e.target.value) })} /></label>
            <label className="field"><span>Failed sign-ins</span><input type="number" min="0" max="100" value={event.failed_auth_attempts} onChange={(e) => setEvent({ ...event, failed_auth_attempts: Number(e.target.value) })} /></label>
            <label className="field"><span>Data transferred (bytes)</span><input type="number" min="0" value={event.bytes_transferred} onChange={(e) => setEvent({ ...event, bytes_transferred: Number(e.target.value) })} /></label>
          </div>
        </details>

        <label className="escalation-check"><input type="checkbox" checked={event.privilege_escalated} onChange={(e) => setEvent({ ...event, privilege_escalated: e.target.checked })} /><span><strong>Privilege escalation occurred</strong><small>The account gained higher permissions during this session</small></span></label>

        <button className="button button-primary submit-button" disabled={busy}>
          {busy ? <><span className="spinner" /> Evaluating the session…</> : <>Evaluate session <span>→</span></>}
        </button>
        <p className="form-assurance"><span>✓</span> The result includes an explanation and recommended next step.</p>
      </form>
    </section>
  );
}
