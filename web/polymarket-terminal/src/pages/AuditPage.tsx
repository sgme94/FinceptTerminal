import { useEffect, useMemo, useState } from "react";
import {
  getAuditEvents,
  getCandidates,
  getPaperPositions,
  getPaperTrades,
  getSignals,
  getSkips,
  getTradeProposals
} from "../api/client";
import type {
  AuditEvent,
  MarketCandidate,
  PaperPosition,
  PaperTrade,
  SignalRow,
  SkipRow,
  TradeProposal
} from "../api/types";
import {
  mockAuditEvents,
  mockMarketCandidates,
  mockPaperPositions,
  mockPaperTrades,
  mockSignals,
  mockSkips,
  mockTradeProposals
} from "../data/mockTerminalData";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";

type AuditTab = "trades" | "signals" | "positions" | "candidates" | "skips" | "proposals";

function statusTransition(event: AuditEvent) {
  const beforeStatus =
    event.before && typeof event.before === "object" && "status" in event.before
      ? String(event.before.status)
      : "";
  const afterStatus =
    event.after && typeof event.after === "object" && "status" in event.after
      ? String(event.after.status)
      : "";

  return beforeStatus && afterStatus ? `${beforeStatus} -> ${afterStatus}` : "No transition";
}

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
    key: "status",
    header: "Status",
    render: (row) => row.status
  }
];

const tradeColumns: Array<DenseDataTableColumn<PaperTrade>> = [
  {
    key: "id",
    header: "Trade",
    render: (row) => row.id
  },
  {
    key: "asset",
    header: "Asset",
    render: (row) => row.assetId
  },
  {
    key: "side",
    header: "Side",
    render: (row) => row.side
  },
  {
    key: "price",
    header: "Price",
    align: "right",
    render: (row) => row.price.toFixed(2)
  }
];

const positionColumns: Array<DenseDataTableColumn<PaperPosition>> = [
  {
    key: "id",
    header: "Position",
    render: (row) => row.id
  },
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
    key: "exposure",
    header: "Exposure",
    align: "right",
    render: (row) => row.exposureUsd.toFixed(2)
  }
];

const candidateColumns: Array<DenseDataTableColumn<MarketCandidate>> = [
  {
    key: "id",
    header: "Candidate",
    render: (row) => row.id
  },
  {
    key: "question",
    header: "Question",
    render: (row) => row.question
  },
  {
    key: "liquidity",
    header: "Liquidity",
    align: "right",
    render: (row) => row.liquidityUsd.toFixed(0)
  }
];

const signalColumns: Array<DenseDataTableColumn<SignalRow>> = [
  {
    key: "id",
    header: "Signal",
    render: (row) => row.id
  },
  {
    key: "label",
    header: "Label",
    render: (row) => row.label
  },
  {
    key: "edge",
    header: "Edge bps",
    align: "right",
    render: (row) => row.edgeBps
  }
];

const skipColumns: Array<DenseDataTableColumn<SkipRow>> = [
  {
    key: "id",
    header: "Skip",
    render: (row) => row.id
  },
  {
    key: "market",
    header: "Market",
    render: (row) => row.marketId
  },
  {
    key: "reason",
    header: "Reason",
    render: (row) => row.reason
  }
];

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>(mockAuditEvents);
  const [proposals, setProposals] = useState<TradeProposal[]>(mockTradeProposals);
  const [trades, setTrades] = useState<PaperTrade[]>(mockPaperTrades);
  const [positions, setPositions] = useState<PaperPosition[]>(mockPaperPositions);
  const [candidates, setCandidates] = useState<MarketCandidate[]>(mockMarketCandidates);
  const [signals, setSignals] = useState<SignalRow[]>(mockSignals);
  const [skips, setSkips] = useState<SkipRow[]>(mockSkips);
  const [deploymentFilter, setDeploymentFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [resultFilter, setResultFilter] = useState("all");
  const [activeTab, setActiveTab] = useState<AuditTab>("trades");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    Promise.all([
      getAuditEvents(),
      getTradeProposals(),
      getPaperTrades(),
      getPaperPositions(),
      getCandidates(),
      getSignals(),
      getSkips()
    ])
      .then(([nextEvents, nextProposals, nextTrades, nextPositions, nextCandidates, nextSignals, nextSkips]) => {
        if (isMounted) {
          setEvents(nextEvents);
          setProposals(nextProposals);
          setTrades(nextTrades);
          setPositions(nextPositions);
          setCandidates(nextCandidates);
          setSignals(nextSignals);
          setSkips(nextSkips);
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

  const filteredEvents = useMemo(
    () =>
      events.filter((event) => {
        const matchesDeployment =
          deploymentFilter.trim() === "" || event.deploymentId.includes(deploymentFilter.trim());
        const matchesAction = actionFilter === "all" || event.action === actionFilter;
        const matchesResult = resultFilter === "all" || event.result === resultFilter;

        return matchesDeployment && matchesAction && matchesResult;
      }),
    [actionFilter, deploymentFilter, events, resultFilter]
  );
  const filteredProposals = useMemo(
    () =>
      proposals.filter(
        (proposal) =>
          deploymentFilter.trim() === "" || proposal.deploymentId.includes(deploymentFilter.trim())
      ),
    [deploymentFilter, proposals]
  );
  const filteredTrades = useMemo(
    () =>
      trades.filter(
        (trade) => deploymentFilter.trim() === "" || trade.deploymentId.includes(deploymentFilter.trim())
      ),
    [deploymentFilter, trades]
  );
  const filteredPositions = useMemo(
    () =>
      positions.filter(
        (position) =>
          deploymentFilter.trim() === "" || position.deploymentId.includes(deploymentFilter.trim())
      ),
    [deploymentFilter, positions]
  );
  const filteredCandidates = useMemo(() => candidates, [candidates]);
  const filteredSignals = useMemo(() => signals, [signals]);
  const filteredSkips = useMemo(() => skips, [skips]);

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Audit log</p>
          <h1>Audit</h1>
        </div>
        <StatusPill label="append-only warning" tone="warn" />
      </div>

      <p className="page-warning">
        Append-only warning: audit events are displayed as immutable records; corrections must be
        appended as new events.
      </p>

      <div className="filter-row" aria-label="Audit filters">
        <label>
          Deployment
          <input
            value={deploymentFilter}
            onChange={(event) => setDeploymentFilter(event.target.value)}
            placeholder="deployment id"
          />
        </label>
        <label>
          Action
          <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)}>
            <option value="all">All actions</option>
            <option value="start">start</option>
            <option value="stop">stop</option>
            <option value="approve">approve</option>
            <option value="reject">reject</option>
          </select>
        </label>
        <label>
          Result
          <select value={resultFilter} onChange={(event) => setResultFilter(event.target.value)}>
            <option value="all">All results</option>
            <option value="accepted">accepted</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
            <option value="skipped">skipped</option>
          </select>
        </label>
      </div>

      <ul className="audit-event-list" aria-label="Audit event list">
        {filteredEvents.map((event) => (
          <li key={event.id}>
            <span>{event.createdAt}</span>
            <strong>{event.action ?? event.level}</strong>
            <span>{event.result ?? "recorded"}</span>
            <span>{event.message}</span>
            <small>{statusTransition(event)}</small>
          </li>
        ))}
      </ul>

      <div className="tab-row" role="tablist" aria-label="Audit projections">
        {(["trades", "signals", "positions", "candidates", "skips", "proposals"] as AuditTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "trades" ? (
        <DenseDataTable
          caption="Paper trade audit rows"
          columns={tradeColumns}
          rows={filteredTrades}
          getRowKey={(row) => row.id}
          emptyTitle="No trades"
          emptyDescription="No paper trade rows are available."
        />
      ) : null}

      {activeTab === "signals" ? (
        <DenseDataTable
          caption="Signal audit rows"
          columns={signalColumns}
          rows={filteredSignals}
          getRowKey={(row) => row.id}
          emptyTitle="No signals"
          emptyDescription="No signal rows are available."
        />
      ) : null}

      {activeTab === "positions" ? (
        <DenseDataTable
          caption="Position audit rows"
          columns={positionColumns}
          rows={filteredPositions}
          getRowKey={(row) => row.id}
          emptyTitle="No positions"
          emptyDescription="No paper position rows are available."
        />
      ) : null}

      {activeTab === "candidates" ? (
        <DenseDataTable
          caption="Candidate audit rows"
          columns={candidateColumns}
          rows={filteredCandidates}
          getRowKey={(row) => row.id}
          emptyTitle="No candidates"
          emptyDescription="No candidate rows are available."
        />
      ) : null}

      {activeTab === "skips" ? (
        <DenseDataTable
          caption="Skip audit rows"
          columns={skipColumns}
          rows={filteredSkips}
          getRowKey={(row) => row.id}
          emptyTitle="No skips"
          emptyDescription="No skip rows are available."
        />
      ) : null}

      {activeTab === "proposals" ? (
        <DenseDataTable
          caption="Proposal audit projection"
          columns={proposalColumns}
          rows={filteredProposals}
          getRowKey={(row) => row.id}
          emptyTitle="No proposals"
          emptyDescription="No proposal audit rows are available."
        />
      ) : null}
    </section>
  );
}
