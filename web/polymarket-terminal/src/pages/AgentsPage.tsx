import { useEffect, useMemo, useState } from "react";
import { fetchPolyAlphaCockpit } from "../api/client";
import type {
  PolyAlphaCockpit,
  PolyAlphaOpportunity,
  PolyAlphaPromotionDecision,
  PolyAlphaScanRun,
  PolyAlphaShadowSignal,
  PolyAlphaValidationResult
} from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";
import {
  mockPolyAlphaOpportunities,
  mockPolyAlphaPromotionDecisions,
  mockPolyAlphaScanRuns,
  mockPolyAlphaShadowSignals,
  mockPolyAlphaValidationResults
} from "../data/mockTerminalData";

const initialCockpit: PolyAlphaCockpit = {
  opportunities: mockPolyAlphaOpportunities,
  scanRuns: mockPolyAlphaScanRuns,
  shadowSignals: mockPolyAlphaShadowSignals,
  validations: mockPolyAlphaValidationResults,
  promotions: mockPolyAlphaPromotionDecisions
};

function formatPercent(value: number) {
  return `${value}%`;
}

function formatEdge(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function promotionTone(decision: PolyAlphaPromotionDecision["decision"]): "ok" | "warn" | "danger" | "neutral" {
  if (decision === "promote") {
    return "ok";
  }

  if (decision === "reject") {
    return "danger";
  }

  if (decision === "watch") {
    return "warn";
  }

  return "neutral";
}

const opportunityColumns: Array<DenseDataTableColumn<PolyAlphaOpportunity>> = [
  {
    key: "title",
    header: "Opportunity",
    render: (row) => row.title
  },
  {
    key: "probability",
    header: "Market -> estimate",
    render: (row) => `${formatPercent(row.marketProbability)} -> ${formatPercent(row.estimatedProbability)}`
  },
  {
    key: "edge",
    header: "Edge",
    align: "right",
    render: (row) => formatEdge(row.edge)
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusPill label={row.status} tone={row.status === "validated" ? "ok" : "warn"} />
  }
];

const researchColumns: Array<DenseDataTableColumn<PolyAlphaOpportunity>> = [
  {
    key: "opportunity",
    header: "Opportunity",
    render: (row) => row.title
  },
  {
    key: "reason",
    header: "Primary reason",
    render: (row) => row.primaryReason
  },
  {
    key: "updated",
    header: "Updated",
    render: (row) => row.updatedAt
  }
];

const shadowColumns: Array<DenseDataTableColumn<PolyAlphaShadowSignal & { validation?: PolyAlphaValidationResult }>> = [
  {
    key: "signal",
    header: "Signal",
    render: (row) => row.id
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusPill label={row.status} tone={row.status === "validated" ? "ok" : "warn"} />
  },
  {
    key: "clv",
    header: "CLV",
    align: "right",
    render: (row) => (row.validation ? row.validation.closingLineValue.toFixed(2) : "")
  },
  {
    key: "brier",
    header: "Brier",
    align: "right",
    render: (row) => (row.validation ? row.validation.brierScore.toFixed(2) : "")
  }
];

const promotionColumns: Array<DenseDataTableColumn<PolyAlphaPromotionDecision>> = [
  {
    key: "promotion",
    header: "Decision",
    render: (row) => <StatusPill label={row.decision} tone={promotionTone(row.decision)} />
  },
  {
    key: "opportunity",
    header: "Opportunity",
    render: (row) => row.opportunityId
  },
  {
    key: "proposal",
    header: "Proposal",
    render: (row) => row.proposalId || "paper review"
  },
  {
    key: "reason",
    header: "Reason",
    render: (row) => row.reason
  }
];

const scanColumns: Array<DenseDataTableColumn<PolyAlphaScanRun>> = [
  {
    key: "scan",
    header: "Scan",
    render: (row) => row.id
  },
  {
    key: "status",
    header: "Status",
    render: (row) => row.status
  },
  {
    key: "counts",
    header: "Counts",
    render: (row) => `${row.scannedCount} scanned / ${row.watchCount} watch / ${row.createdOpportunityCount} created`
  },
  {
    key: "started",
    header: "Started",
    render: (row) => row.startedAt
  }
];

export function AgentsPage() {
  const [cockpit, setCockpit] = useState<PolyAlphaCockpit>(initialCockpit);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    fetchPolyAlphaCockpit()
      .then((nextCockpit) => {
        if (isMounted) {
          setCockpit(nextCockpit);
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

  const validationsBySignal = useMemo(
    () => new Map(cockpit.validations.map((validation) => [validation.shadowSignalId, validation])),
    [cockpit.validations]
  );
  const shadowPerformance = useMemo(
    () => cockpit.shadowSignals.map((signal) => ({ ...signal, validation: validationsBySignal.get(signal.id) })),
    [cockpit.shadowSignals, validationsBySignal]
  );
  const needsResearch = useMemo(
    () => cockpit.opportunities.filter((opportunity) => opportunity.status === "shadow"),
    [cockpit.opportunities]
  );
  const readyForPromotion = useMemo(
    () => cockpit.promotions.filter((promotion) => promotion.decision === "promote"),
    [cockpit.promotions]
  );
  const failedPromotions = useMemo(
    () => cockpit.promotions.filter((promotion) => promotion.decision === "reject" || promotion.criticBlockers.length > 0),
    [cockpit.promotions]
  );
  const riskQueueCandidates = useMemo(
    () => readyForPromotion.filter((promotion) => promotion.proposalId.trim() !== ""),
    [readyForPromotion]
  );

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Advisory agent console</p>
          <h1>Poly Alpha Cockpit</h1>
        </div>
        <div className="status-row" aria-label="Agent limits">
          <StatusPill label="Agents cannot trade" tone="ok" />
          <StatusPill label="paper-only" tone="ok" />
        </div>
      </div>

      <p className="page-warning">
        Poly Alpha findings are advisory and paper-only. No live execution or order routing is exposed here.
      </p>

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Today's opportunities</h2>
          <DenseDataTable
            caption="Today's opportunities"
            columns={opportunityColumns}
            rows={cockpit.opportunities}
            getRowKey={(row) => row.id}
            emptyTitle="No opportunities"
            emptyDescription="No Poly Alpha opportunities are available."
          />
        </div>

        <div className="page-section">
          <h2>Needs research</h2>
          <DenseDataTable
            caption="Needs research"
            columns={researchColumns}
            rows={needsResearch}
            getRowKey={(row) => row.id}
            emptyTitle="No research candidates"
            emptyDescription="No opportunities currently need research."
          />
        </div>
      </div>

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Shadow performance</h2>
          <DenseDataTable
            caption="Shadow performance"
            columns={shadowColumns}
            rows={shadowPerformance}
            getRowKey={(row) => row.id}
            emptyTitle="No shadow performance"
            emptyDescription="No shadow signals have validation metrics."
          />
        </div>

        <div className="page-section">
          <h2>scheduled scan runs</h2>
          <DenseDataTable
            caption="Scheduled scan runs"
            columns={scanColumns}
            rows={cockpit.scanRuns}
            getRowKey={(row) => row.id}
            emptyTitle="No scheduled scans"
            emptyDescription="No scan runs have been recorded."
          />
        </div>
      </div>

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Ready for promotion</h2>
          <DenseDataTable
            caption="Ready for promotion"
            columns={promotionColumns}
            rows={readyForPromotion}
            getRowKey={(row) => row.id}
            emptyTitle="No promotion-ready rows"
            emptyDescription="No paper-only promotions are ready."
          />
        </div>

        <div className="page-section">
          <h2>Risk queue candidates</h2>
          <DenseDataTable
            caption="Risk queue candidates"
            columns={promotionColumns}
            rows={riskQueueCandidates}
            getRowKey={(row) => row.id}
            emptyTitle="No risk queue candidates"
            emptyDescription="No promoted proposals are ready for risk review."
          />
        </div>
      </div>

      <div className="page-section">
        <h2>Failed and why</h2>
        <DenseDataTable
          caption="Failed and why"
          columns={promotionColumns}
          rows={failedPromotions}
          getRowKey={(row) => row.id}
          emptyTitle="No failed promotions"
          emptyDescription="No rejected Poly Alpha promotions are available."
        />
      </div>
    </section>
  );
}
