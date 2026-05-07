import { useCallback, useEffect, useMemo, useState } from "react";
import {
  approveTradeProposal,
  getAuditEvents,
  getRiskLimits,
  getSkips,
  getTradeProposals,
  rejectTradeProposal,
  triggerKillSwitch
} from "../api/client";
import type { AuditEvent, RiskLimit, SkipRow, TradeProposal } from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";
import { TerminalButton } from "../components/ui/TerminalButton";
import {
  mockAuditEvents,
  mockRiskLimits,
  mockSkips,
  mockTradeProposals
} from "../data/mockTerminalData";

const CONTROL_ACTOR_CONTEXT = {
  strategy_id: "manual",
  actor_id: "local-user"
} as const;

type RiskData = {
  proposals: TradeProposal[];
  riskLimits: RiskLimit[];
  auditEvents: AuditEvent[];
  skips: SkipRow[];
};

async function fetchRiskData(): Promise<RiskData> {
  const [proposals, riskLimits, auditEvents, skips] = await Promise.all([
    getTradeProposals(),
    getRiskLimits(),
    getAuditEvents(),
    getSkips()
  ]);

  return { proposals, riskLimits, auditEvents, skips };
}

function deriveDeploymentId(proposals: TradeProposal[], auditEvents: AuditEvent[]): string {
  return proposals[0]?.deploymentId || auditEvents[0]?.deploymentId || "default";
}

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function riskTone(status: RiskLimit["status"]): "ok" | "warn" | "danger" {
  if (status === "ok") {
    return "ok";
  }

  if (status === "warn") {
    return "warn";
  }

  return "danger";
}

function proposalTone(status: TradeProposal["status"]): "ok" | "warn" | "danger" | "neutral" {
  if (status === "approved" || status === "filled") {
    return "ok";
  }

  if (status === "rejected" || status === "failed" || status === "cancelled") {
    return "danger";
  }

  if (status === "proposed" || status === "expired") {
    return "warn";
  }

  return "neutral";
}

function canActOnProposal(proposal: TradeProposal) {
  return proposal.status === "proposed" && proposal.source === "api" && proposal.stale !== true;
}

type HistoryRow = {
  id: string;
  type: "skip" | "reject";
  label: string;
  detail: string;
  createdAt: string;
};

export function RiskPage() {
  const [proposals, setProposals] = useState<TradeProposal[]>(mockTradeProposals);
  const [riskLimits, setRiskLimits] = useState<RiskLimit[]>(mockRiskLimits);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>(mockAuditEvents);
  const [skips, setSkips] = useState<SkipRow[]>(mockSkips);
  const [isLoading, setIsLoading] = useState(true);
  const [controlDeploymentId, setControlDeploymentId] = useState(() =>
    deriveDeploymentId(mockTradeProposals, mockAuditEvents)
  );
  const [controlError, setControlError] = useState<string | null>(null);

  const applyRiskData = useCallback((nextData: RiskData) => {
    setProposals(nextData.proposals);
    setRiskLimits(nextData.riskLimits);
    setAuditEvents(nextData.auditEvents);
    setSkips(nextData.skips);
    setControlDeploymentId(deriveDeploymentId(nextData.proposals, nextData.auditEvents));
  }, []);

  const reloadRiskData = useCallback(async () => {
    applyRiskData(await fetchRiskData());
  }, [applyRiskData]);

  useEffect(() => {
    let isMounted = true;

    fetchRiskData()
      .then((nextData) => {
        if (!isMounted) {
          return;
        }

        applyRiskData(nextData);
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [applyRiskData]);

  const historyRows = useMemo<HistoryRow[]>(
    () => [
      ...skips.map((skip) => ({
        id: skip.id,
        type: "skip" as const,
        label: skip.marketId,
        detail: skip.reason,
        createdAt: skip.createdAt
      })),
      ...auditEvents
        .filter((event) => event.action === "reject" || event.result === "rejected")
        .map((event) => ({
          id: event.id,
          type: "reject" as const,
          label: event.entityId ?? "proposal",
          detail: event.reason ?? event.message,
          createdAt: event.createdAt
        }))
    ].sort((left, right) => right.createdAt.localeCompare(left.createdAt)),
    [auditEvents, skips]
  );

  async function handleApprove(proposal: TradeProposal) {
    if (!window.confirm(`Approve ${proposal.id} for paper execution tracking?`)) {
      return;
    }

    setControlError(null);
    try {
      await approveTradeProposal(proposal.id, {
        ...CONTROL_ACTOR_CONTEXT,
        deployment_id: proposal.deploymentId,
        reason: "Approved from paper risk page"
      });
      await reloadRiskData();
    } catch (error) {
      setControlError(error instanceof Error ? error.message : "Risk control request failed");
    }
  }

  async function handleReject(proposal: TradeProposal) {
    if (!window.confirm(`Reject ${proposal.id} from paper risk page?`)) {
      return;
    }

    const reason = "Rejected from paper risk page";
    setControlError(null);
    try {
      await rejectTradeProposal(proposal.id, {
        ...CONTROL_ACTOR_CONTEXT,
        deployment_id: proposal.deploymentId,
        reason
      });
      await reloadRiskData();
    } catch (error) {
      setControlError(error instanceof Error ? error.message : "Risk control request failed");
    }
  }

  async function handleKillSwitch() {
    if (!window.confirm("Trigger the paper kill switch and write an audit event?")) {
      return;
    }

    setControlError(null);
    try {
      await triggerKillSwitch({
        ...CONTROL_ACTOR_CONTEXT,
        deployment_id: controlDeploymentId,
        reason: "Paper kill switch requested from risk page"
      });
      await reloadRiskData();
    } catch (error) {
      setControlError(error instanceof Error ? error.message : "Risk control request failed");
    }
  }

  const proposalColumns: Array<DenseDataTableColumn<TradeProposal>> = [
    {
      key: "proposal",
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
      render: (row) => <StatusPill label={row.status} tone={proposalTone(row.status)} />
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) =>
        canActOnProposal(row) ? (
          <div className="table-action-row">
            <TerminalButton aria-label={`Approve ${row.id}`} tone="accent" onClick={() => void handleApprove(row)}>
              Approve
            </TerminalButton>
            <TerminalButton aria-label={`Reject ${row.id}`} tone="danger" onClick={() => void handleReject(row)}>
              Reject
            </TerminalButton>
          </div>
        ) : row.status === "proposed" ? (
          <span className="workspace-kicker">stale data</span>
        ) : (
          <span className="workspace-kicker">Closed</span>
        )
    }
  ];

  const historyColumns: Array<DenseDataTableColumn<HistoryRow>> = [
    {
      key: "type",
      header: "Type",
      render: (row) => row.type
    },
    {
      key: "label",
      header: "Target",
      render: (row) => row.label
    },
    {
      key: "detail",
      header: "Reason",
      render: (row) => row.detail
    }
  ];

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Paper risk controls</p>
          <h1>Risk</h1>
        </div>
        <div className="status-row">
          <StatusPill label="manual approval" tone="warn" />
          <StatusPill label="paper only" tone="ok" />
        </div>
      </div>
      {controlError ? <p className="page-warning" role="alert">{controlError}</p> : null}

      <div className="page-section">
        <div className="page-header">
          <h2>Risk limits</h2>
          <TerminalButton aria-label="Paper kill switch" tone="danger" onClick={() => void handleKillSwitch()}>
            Paper kill switch
          </TerminalButton>
        </div>
        <div className="metric-grid" aria-label="Risk limits">
          {riskLimits.map((limit) => (
            <div key={limit.id} className="metric-cell">
              <span>{limit.label}</span>
              <strong>{formatUsd(limit.usedUsd)}</strong>
              <small>
                Limit {formatUsd(limit.limitUsd)}
              </small>
              <StatusPill label={limit.status} tone={riskTone(limit.status)} />
            </div>
          ))}
        </div>
      </div>

      <div className="page-section">
        <h2>Proposal approval queue</h2>
        <DenseDataTable
          caption="Proposal approval queue"
          columns={proposalColumns}
          rows={proposals}
          getRowKey={(row) => row.id}
          emptyTitle="No proposals"
          emptyDescription="No paper proposals require review."
        />
      </div>

      <div className="page-section">
        <h2>Skip/reject history</h2>
        <DenseDataTable
          caption="Skip/reject history"
          columns={historyColumns}
          rows={historyRows}
          getRowKey={(row) => row.id}
          emptyTitle="No history"
          emptyDescription="No skip or reject history has been recorded."
        />
      </div>
    </section>
  );
}
