import { useState } from "react";

export interface PqcVaultSummary {
  available: boolean;
  quantumSafe?: boolean;
  algorithm: string;
  itemCount: number;
  provider?: string;
}

export interface PqcEncryptionResult {
  envelope_id: string;
  algorithm: string;
  ciphertext: string;
}

export interface PqcDecryptionResult {
  envelope_id: string;
  plaintext: string;
}

export interface PqcVaultViewProps {
  summary: PqcVaultSummary;
  readOnly?: boolean;
  onEncrypt: (plaintext: string) => Promise<PqcEncryptionResult>;
  onDecrypt: (envelopeId: string) => Promise<PqcDecryptionResult>;
}

type VaultOperation = "encrypt" | "decrypt" | null;

function JsonOutput({ label, value }: { label: string; value: object }) {
  return (
    <div className="vault-raw-output">
      <div className="vault-output-label">
        <span>{label}</span>
        <small>Raw API output</small>
      </div>
      <pre tabIndex={0}>{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

export function PqcVaultView({ summary, readOnly = false, onEncrypt, onDecrypt }: PqcVaultViewProps) {
  const [plaintext, setPlaintext] = useState("test-admin-credential-2026");
  const [encrypted, setEncrypted] = useState<PqcEncryptionResult | null>(null);
  const [decrypted, setDecrypted] = useState<PqcDecryptionResult | null>(null);
  const [operation, setOperation] = useState<VaultOperation>(null);
  const [error, setError] = useState<string | null>(null);

  async function encryptCredential() {
    if (!plaintext.trim()) {
      setError("Enter a test credential before encrypting it.");
      return;
    }

    setOperation("encrypt");
    setError(null);
    setEncrypted(null);
    setDecrypted(null);
    try {
      setEncrypted(await onEncrypt(plaintext));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The credential could not be encrypted.");
    } finally {
      setOperation(null);
    }
  }

  async function decryptCredential() {
    if (!encrypted) return;
    setOperation("decrypt");
    setError(null);
    try {
      setDecrypted(await onDecrypt(encrypted.envelope_id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The credential could not be decrypted.");
    } finally {
      setOperation(null);
    }
  }

  function clearRoundTrip() {
    setEncrypted(null);
    setDecrypted(null);
    setError(null);
  }

  const roundTripMatches = Boolean(decrypted && decrypted.plaintext === plaintext);

  return (
    <main className="enterprise-view vault-view" aria-labelledby="vault-title">
      <header className="enterprise-page-header">
        <div>
          <span className="enterprise-eyebrow">POST-QUANTUM CREDENTIAL SECURITY</span>
          <h1 id="vault-title">PQC vault</h1>
          <p>Test credential-envelope encryption and confirm which cryptographic provider is active.</p>
        </div>
        <div className={`vault-status-pill ${summary.quantumSafe ? "is-online" : summary.available ? "is-compatibility" : "is-offline"}`}>
          <span aria-hidden="true" />
          {summary.quantumSafe ? "ML-KEM provider active" : summary.available ? "Local compatibility mode" : "Vault unavailable"}
        </div>
      </header>

      <section className="vault-summary-grid" aria-label="Vault status">
        <article className="enterprise-stat-card">
          <span>Key encapsulation</span>
          <strong>{summary.algorithm}</strong>
          <small>{summary.quantumSafe ? "ML-KEM provider active" : "Local compatibility mode; PQC requires the OQS runtime"}</small>
        </article>
        <article className="enterprise-stat-card">
          <span>Protected items</span>
          <strong>{summary.itemCount.toLocaleString()}</strong>
          <small>Encrypted credential envelopes</small>
        </article>
        <article className="enterprise-stat-card">
          <span>Runtime provider</span>
          <strong>{summary.provider ?? "Open Quantum Safe"}</strong>
          <small>{summary.available ? "Ready for round-trip verification" : "Runtime check required"}</small>
        </article>
      </section>

      <section className="enterprise-panel vault-workbench" aria-labelledby="vault-test-title">
        <div className="enterprise-panel-heading">
          <div>
            <span className="section-index">ENCRYPTION TEST · 01</span>
            <h2 id="vault-test-title">Verify an encrypt–decrypt round trip</h2>
            <p>The browser sends this synthetic value to the prototype API; browser storage is not used.</p>
          </div>
          {(encrypted || decrypted) && <button className="text-button" type="button" onClick={clearRoundTrip}>Clear outputs</button>}
        </div>

        <div className="vault-test-layout">
          <form className="vault-input-panel" onSubmit={(event) => { event.preventDefault(); void encryptCredential(); }}>
            {readOnly && <p className="enterprise-access-note">Read-only analyst view. Switch to <strong>Security admin</strong> in the top bar to operate the vault.</p>}
            <label htmlFor="vault-test-credential">Test credential</label>
            <input
              id="vault-test-credential"
              type="text"
              autoComplete="off"
              value={plaintext}
              onChange={(event) => setPlaintext(event.target.value)}
              disabled={operation !== null || encrypted !== null}
            />
            <p className="field-help">Use synthetic data only. Production secrets should be entered through an approved PAM workflow.</p>
            <button className="enterprise-primary-button" type="submit" disabled={!summary.available || readOnly || operation !== null}>
              {operation === "encrypt" ? "Encrypting…" : "Encrypt credential"}
              <span aria-hidden="true">→</span>
            </button>
            {encrypted && (
              <button className="enterprise-secondary-button" type="button" onClick={() => void decryptCredential()} disabled={operation !== null}>
                {operation === "decrypt" ? "Decrypting…" : "Decrypt and verify"}
              </button>
            )}
            {error && <p className="enterprise-error" role="alert">{error}</p>}
          </form>

          <div className="vault-output-stack" aria-live="polite">
            {!encrypted && (
              <div className="enterprise-empty-state compact">
                <span className="empty-state-glyph" aria-hidden="true">⌁</span>
                <strong>No encrypted envelope yet</strong>
                <p>Encrypt the test credential to inspect the algorithm, envelope ID, and ciphertext.</p>
              </div>
            )}
            {encrypted && <JsonOutput label="Encrypted envelope" value={encrypted} />}
            {decrypted && <JsonOutput label="Decrypted response" value={decrypted} />}
            {decrypted && (
              <div className={`vault-verification ${roundTripMatches ? "is-valid" : "is-invalid"}`} role="status">
                <span aria-hidden="true">{roundTripMatches ? "✓" : "!"}</span>
                <div>
                  <strong>{roundTripMatches ? "Round trip verified" : "Plaintext mismatch"}</strong>
                  <p>{roundTripMatches ? "The decrypted value exactly matches the original test credential." : "Do not use this envelope; the decrypted value is not identical."}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <aside className="vault-threat-note">
        <strong>THREAT MODEL</strong>
        <p>Adversaries can retain encrypted data and attempt decryption as capabilities improve. PQC migration reduces exposure to that scenario.</p>
      </aside>
    </main>
  );
}
