import { EmptyStatePanel } from "../components/ui/EmptyStatePanel";
import { StatusPill } from "../components/ui/StatusPill";

const adapters = [
  "OpenBB adapter placeholder",
  "public-apis adapter placeholder",
  "Sherlock adapter placeholder"
];

export function DataPage() {
  return (
    <section className="workspace-panel page-stack">
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Read-only data plane</p>
          <h1>Data</h1>
        </div>
        <div className="status-row" aria-label="Data mode">
          <StatusPill label="paper-only" tone="ok" />
          <StatusPill label="no secrets" tone="ok" />
        </div>
      </div>

      <div className="page-grid">
        <div className="page-section">
          <h2>Polymarket source status</h2>
          <div className="detail-stack">
            <div className="detail-row">
              <span>Source</span>
              <strong>Polymarket public markets</strong>
            </div>
            <div className="detail-row">
              <span>Status</span>
              <StatusPill label="mock adapter healthy" tone="mock" />
            </div>
            <p className="detail-copy">Public read path only. No CLOB order placement is connected.</p>
          </div>
        </div>

        <div className="page-section">
          <h2>Cache health</h2>
          <div className="detail-stack">
            <div className="detail-row">
              <span>Snapshot cache</span>
              <strong>Warm mock snapshot</strong>
            </div>
            <div className="detail-row">
              <span>Freshness target</span>
              <strong>Under 60s for local mock data</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="page-section">
        <h2>Adapter placeholders</h2>
        <div className="detail-badges">
          {adapters.map((adapter) => (
            <StatusPill key={adapter} label={adapter} tone="warn" />
          ))}
        </div>
      </div>

      <div className="page-section">
        <h2>Dataroom</h2>
        <EmptyStatePanel
          title="Dataroom upload disabled"
          description="No credentials, private keys, or API secrets are requested in the MVP."
        />
      </div>
    </section>
  );
}
