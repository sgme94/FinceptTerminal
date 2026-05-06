import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { EmptyStatePanel } from "../components/ui/EmptyStatePanel";
import { StatusPill } from "../components/ui/StatusPill";

type FindingRow = {
  id: string;
  finding: string;
  dissent: string;
  confidence: string;
  verification: "unverified" | "reviewed";
};

const findings: FindingRow[] = [
  {
    id: "finding-fed",
    finding: "Rate-cut odds diverge from speaker tone",
    dissent: "Liquidity is thin outside top markets",
    confidence: "62%",
    verification: "unverified"
  },
  {
    id: "finding-btc",
    finding: "Crypto volume clusters around end-of-month strikes",
    dissent: "Headline sensitivity remains high",
    confidence: "58%",
    verification: "reviewed"
  }
];

const columns: Array<DenseDataTableColumn<FindingRow>> = [
  {
    key: "finding",
    header: "Finding",
    render: (row) => row.finding
  },
  {
    key: "dissent",
    header: "Dissent",
    render: (row) => row.dissent
  },
  {
    key: "confidence",
    header: "Confidence",
    render: (row) => row.confidence
  },
  {
    key: "verification",
    header: "Verification",
    render: (row) => <StatusPill label={row.verification} tone={row.verification === "unverified" ? "warn" : "ok"} />
  }
];

export function AgentsPage() {
  return (
    <section className="workspace-panel page-stack">
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Advisory agent console</p>
          <h1>Agents</h1>
        </div>
        <div className="status-row" aria-label="Agent limits">
          <StatusPill label="Agents cannot trade" tone="ok" />
          <StatusPill label="paper-only" tone="ok" />
        </div>
      </div>

      <p className="page-warning">Unverified generated claims are marked unverified.</p>

      <div className="page-grid">
        <div className="page-section">
          <h2>Event sentinels</h2>
          <div className="detail-stack">
            <div className="detail-row">
              <span>Macro calendar sentinel</span>
              <strong>Watching rate and inflation windows</strong>
            </div>
            <div className="detail-row">
              <span>Market movement sentinel</span>
              <strong>Flags probability jumps above threshold</strong>
            </div>
          </div>
        </div>

        <div className="page-section">
          <h2>Research cycles</h2>
          <div className="detail-stack">
            <div className="detail-row">
              <span>Cycle cadence</span>
              <strong>Mock 15m research sweep</strong>
            </div>
            <div className="detail-row">
              <span>Output</span>
              <strong>Findings, dissent, confidence only</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="page-section">
        <h2>Findings</h2>
        <DenseDataTable
          caption="Findings and dissent"
          columns={columns}
          rows={findings}
          getRowKey={(row) => row.id}
          emptyTitle="No agent findings"
          emptyDescription="No advisory research findings are available."
        />
      </div>

      <div className="page-grid">
        {["TradingAgents placeholder", "dexter placeholder", "MiroFish placeholder"].map((title) => (
          <div className="page-section" key={title}>
            <EmptyStatePanel title={title} description="Disabled placeholder. No live execution or order routing." />
          </div>
        ))}
      </div>
    </section>
  );
}
