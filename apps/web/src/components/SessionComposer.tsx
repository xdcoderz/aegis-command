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

  async function submit(e: FormEvent) {
    e.preventDefault();
    await onSubmit({ ...event, session_id: `${event.session_id.split("-").slice(0, -1).join("-")}-${Date.now()}` });
  }

  return (
    <section className="composer card">
      <div className="section-heading">
        <div><p className="eyebrow">Session replay</p><h2>Evaluation console</h2></div>
        <div className="preset-switch">
          <button type="button" onClick={() => setEvent(normalPreset)}>Normal</button>
          <button type="button" className="active" onClick={() => setEvent(maliciousPreset)}>Anomalous</button>
        </div>
      </div>
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>User<input value={event.user_id} onChange={(e) => setEvent({ ...event, user_id: e.target.value })} /></label>
          <label>Role<input value={event.role} onChange={(e) => setEvent({ ...event, role: e.target.value })} /></label>
          <label>Resource<input value={event.resource} onChange={(e) => setEvent({ ...event, resource: e.target.value })} /></label>
          <label>Source IP<input value={event.source_ip} onChange={(e) => setEvent({ ...event, source_ip: e.target.value })} /></label>
        </div>
        <label>Commands<textarea rows={4} value={event.commands.join("\n")} onChange={(e) => setEvent({ ...event, commands: e.target.value.split("\n").filter(Boolean) })} /></label>
        <div className="signal-row">
          <label><input type="checkbox" checked={event.privilege_escalated} onChange={(e) => setEvent({ ...event, privilege_escalated: e.target.checked })} /> Privilege escalation</label>
          <span>{(event.bytes_transferred / 1_000_000).toFixed(1)} MB transferred</span>
          <span>Sensitivity {Math.round(event.resource_sensitivity * 100)}%</span>
        </div>
        <button className="primary" disabled={busy}>{busy ? "Evaluating…" : "Evaluate session"}<span>→</span></button>
      </form>
    </section>
  );
}

