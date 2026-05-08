import { useEffect, useMemo, useState } from "react";
import { getTerminalSnapshot } from "../api/client";
import type { AuditEvent, PaperPosition, SignalRow, TerminalStatus, TradeProposal } from "../api/types";
import { mockTerminalSnapshot } from "../data/mockTerminalData";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { EmptyStatePanel } from "../components/ui/EmptyStatePanel";
import { StatusPill } from "../components/ui/StatusPill";

type RecentRow = {
  id: string;
  kind: "signal" | "fill" | "skip";
  label: string;
  detail: string;
  createdAt: string;
};

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD"
  }).format(value);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function buildRecentRows(signals: SignalRow[], auditEvents: AuditEvent[]): RecentRow[] {
  const signalRows = signals.map((signal) => ({
    id: signal.id,
    kind: "signal" as const,
    label: signal.label,
    detail: `${signal.direction.toUpperCase()} ${signal.confidence}% confidence`,
    createdAt: signal.updatedAt
  }));

  const auditRows = auditEvents
    .filter(
      (event) =>
        event.action === "skip" ||
        event.result === "skipped" ||
        event.action === "fill_simulated" ||
        event.action === "fill" ||
        event.result === "filled"
    )
    .map((event) => ({
      id: event.id,
      kind:
        event.action === "fill_simulated" || event.action === "fill" || event.result === "filled"
          ? ("fill" as const)
          : ("skip" as const),
      label: event.message,
      detail: event.reason ?? event.result ?? event.level,
      createdAt: event.createdAt
    }));

  return [...auditRows, ...signalRows].sort((left, right) =>
    right.createdAt.localeCompare(left.createdAt)
  ).slice(0, 6);
}

const positionColumns: Array<DenseDataTableColumn<PaperPosition>> = [
  {
    key: "asset",
    header: "Asset",
    render: (row) => row.assetId
  },
  {
    key: "size",
    header: "Size",
    align: "right",
    render: (row) => row.size.toFixed(2)
  },
  {
    key: "avg",
    header: "Avg",
    align: "right",
    render: (row) => row.avgPrice.toFixed(2)
  },
  {
    key: "exposure",
    header: "Exposure",
    align: "right",
    render: (row) => formatUsd(row.exposureUsd)
  },
  {
    key: "pnl",
    header: "Realized PnL",
    align: "right",
    render: (row) => formatUsd(row.realizedPnl)
  }
];

const proposalColumns: Array<DenseDataTableColumn<TradeProposal>> = [
  {
    key: "id",
    header: "Proposal",
    render: (row) => row.id
  },
  {
    key: "market",
    header: "Market",
    render: (row) => row.marketId
  },
  {
    key: "size",
    header: "Size",
    align: "right",
    render: (row) => formatUsd(row.sizeUsd)
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusPill label={row.status} tone="warn" />
  }
];

const recentColumns: Array<DenseDataTableColumn<RecentRow>> = [
  {
    key: "kind",
    header: "Type",
    render: (row) => row.kind
  },
  {
    key: "label",
    header: "Event",
    render: (row) => row.label
  },
  {
    key: "detail",
    header: "Detail",
    render: (row) => row.detail
  }
];

export function OverviewPage() {
  const [snapshot, setSnapshot] = useState<TerminalStatus>(mockTerminalSnapshot);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    getTerminalSnapshot()
      .then((nextSnapshot) => {
        if (isMounted) {
          setSnapshot(nextSnapshot);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const pendingProposals = useMemo(
    () => snapshot.proposals.filter((proposal) => proposal.status === "proposed"),
    [snapshot.proposals]
  );
  const recentRows = useMemo(
    () => buildRecentRows(snapshot.signals, snapshot.auditEvents),
    [snapshot.signals, snapshot.auditEvents]
  );
  const liveEnabled = snapshot.status.liveEnabled === true;
  const modeLabel = snapshot.status.mode === "paper" ? "Paper mode" : "Advisory mode";
  const realizedPnl = snapshot.positions.reduce((total, position) => total + position.realizedPnl, 0);

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Bot status</p>
          <h1>Overview</h1>
        </div>
        <div className="status-row" aria-label="Bot status header">
          <StatusPill label={snapshot.status.state} tone={snapshot.status.state === "online" ? "ok" : "warn"} />
          <StatusPill label={modeLabel} tone="warn" />
          <StatusPill label={liveEnabled ? "Live enabled" : "Live disabled"} tone={liveEnabled ? "danger" : "ok"} />
          {snapshot.status.source === "mock" ? <StatusPill label="mock fallback" tone="mock" /> : null}
        </div>
      </div>

      <div className="metric-grid" aria-label="PnL and exposure metrics">
        <div className="metric-cell">
          <span>PnL</span>
          <strong>{formatUsd(realizedPnl)}</strong>
          <small>Paper positions realized PnL</small>
        </div>
        <div className="metric-cell">
          <span>Exposure</span>
          <strong>{formatUsd(snapshot.status.exposureUsd)}</strong>
          <small>{snapshot.status.activeMarkets} active markets</small>
        </div>
        <div className="metric-cell">
          <span>Pending proposals</span>
          <strong>{pendingProposals.length}</strong>
          <small>Paper approval queue only</small>
        </div>
      </div>

      <div className="page-grid">
        <div className="page-section">
          <h2>Open positions</h2>
          <DenseDataTable
            caption="Open positions"
            columns={positionColumns}
            rows={snapshot.positions}
            getRowKey={(row) => row.id}
            emptyTitle="No open positions"
            emptyDescription="No paper positions are open."
          />
        </div>
        <div className="page-section">
          <h2>Pending proposals</h2>
          <DenseDataTable
            caption="Pending proposals preview"
            columns={proposalColumns}
            rows={pendingProposals}
            getRowKey={(row) => row.id}
            emptyTitle="No pending proposals"
            emptyDescription="The paper approval queue is empty."
          />
        </div>
      </div>

      <div className="page-section">
        <h2>Recent signals/fills/skips</h2>
        <DenseDataTable
          caption="Recent signals/fills/skips"
          columns={recentColumns}
          rows={recentRows}
          getRowKey={(row) => row.id}
          emptyTitle="No recent activity"
          emptyDescription="No signals, fills, or skip events are available."
        />
      </div>

      <div className="page-section">
        <h2>Agent composer placeholder</h2>
        <EmptyStatePanel
          title="Agent composer placeholder"
          description={`Paper-only command drafting area. Live trading remains disabled; max proposal probability shown as ${
            pendingProposals[0] ? formatPercent(pendingProposals[0].price) : "n/a"
          }.`}
        />
      </div>
    </section>
  );
}
