import { useState } from "react";

export type EnterpriseRole = "SOC_ANALYST" | "SECURITY_ADMIN";
export type SsoProvider = "BANK_SSO" | "MICROSOFT_ENTRA";

export interface MockSsoIdentity {
  displayName: string;
  email: string;
  role: EnterpriseRole;
  provider: SsoProvider;
}

export interface MockSsoLoginProps {
  onLogin: (identity: MockSsoIdentity) => void | Promise<void>;
  busy?: boolean;
  productName?: string;
}

export function MockSsoLogin({ onLogin, busy = false, productName = "Aegis Command" }: MockSsoLoginProps) {
  const [role, setRole] = useState<EnterpriseRole>("SOC_ANALYST");
  const [error, setError] = useState<string | null>(null);

  async function continueWith(provider: SsoProvider) {
    setError(null);
    const identity: MockSsoIdentity = role === "SOC_ANALYST"
      ? { displayName: "Adittya Sharma", email: "adittya.sharma@bank.demo", role, provider }
      : { displayName: "Adittya Sharma", email: "adittya.sharma+admin@bank.demo", role, provider };
    try {
      await onLogin(identity);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operating identity could not be created.");
    }
  }

  return (
    <main className="sso-login-shell">
      <section className="sso-brand-panel" aria-label={`${productName} overview`}>
        <div className="sso-brand-lockup"><span className="sso-brand-mark" aria-hidden="true">FS</span><strong>{productName}</strong></div>
        <div className="sso-brand-copy">
          <span className="enterprise-eyebrow">PRIVILEGED ACCESS DEFENSE</span>
          <h1>Review privileged activity.<br />Contain confirmed risk.</h1>
          <p>Monitor privileged sessions, investigate anomalies, apply access controls, and retain an audit trail.</p>
        </div>
        <div className="sso-assurance-row">
          <span><i aria-hidden="true">✓</i> Risk factors shown</span>
          <span><i aria-hidden="true">✓</i> Response controls</span>
          <span><i aria-hidden="true">✓</i> PQC runtime status</span>
        </div>
      </section>

      <section className="sso-form-panel" aria-labelledby="sso-title">
        <div className="sso-form-card">
          <span className="sso-demo-chip">DEMONSTRATION ENVIRONMENT</span>
          <h2 id="sso-title">Sign in to the command center</h2>
          <p>Select an operating role. Its permissions apply throughout the console.</p>

          <fieldset className="sso-role-picker">
            <legend>Operating role</legend>
            <label className={role === "SOC_ANALYST" ? "is-selected" : ""}>
              <input type="radio" name="demo-role" value="SOC_ANALYST" checked={role === "SOC_ANALYST"} onChange={() => setRole("SOC_ANALYST")} />
              <span><strong>SOC analyst</strong><small>Investigate sessions and take response action</small></span>
              <i aria-hidden="true">{role === "SOC_ANALYST" ? "●" : "○"}</i>
            </label>
            <label className={role === "SECURITY_ADMIN" ? "is-selected" : ""}>
              <input type="radio" name="demo-role" value="SECURITY_ADMIN" checked={role === "SECURITY_ADMIN"} onChange={() => setRole("SECURITY_ADMIN")} />
              <span><strong>Security admin</strong><small>Manage policy thresholds and the PQC vault</small></span>
              <i aria-hidden="true">{role === "SECURITY_ADMIN" ? "●" : "○"}</i>
            </label>
          </fieldset>

          <div className="sso-provider-buttons">
            <button className="enterprise-primary-button" type="button" disabled={busy} onClick={() => void continueWith("BANK_SSO")}><span className="provider-glyph" aria-hidden="true">B</span>{busy ? "Signing in…" : "Continue with Bank SSO"}</button>
            <button className="enterprise-secondary-button" type="button" disabled={busy} onClick={() => void continueWith("MICROSOFT_ENTRA")}><span className="provider-glyph provider-microsoft" aria-hidden="true">⊞</span>Continue with Microsoft Entra</button>
          </div>
          <p className="sso-security-note"><span aria-hidden="true">⌾</span>Mock sign-in for this prototype. No external identity provider is contacted.</p>
          {error && <p className="enterprise-error" role="alert">{error}</p>}
        </div>
        <footer>Aegis Command · Controlled demonstration environment</footer>
      </section>
    </main>
  );
}
