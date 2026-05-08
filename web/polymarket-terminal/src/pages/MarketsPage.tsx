import { useEffect, useMemo, useState } from "react";
import {
  fetchPolyAlphaEvidencePacks,
  fetchPolyAlphaLinks,
  fetchPolyAlphaMarketSnapshots,
  fetchPolyAlphaOpportunities,
  getTerminalSnapshot
} from "../api/client";
import type {
  MarketCandidate,
  OrderBookSnapshot,
  PolyAlphaEventMarketLink,
  PolyAlphaEvidencePack,
  PolyAlphaMarketSnapshot,
  PolyAlphaOpportunity,
  TerminalStatus
} from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { OrderBookSummary } from "../components/ui/OrderBookSummary";
import { ProbabilityChart } from "../components/ui/ProbabilityChart";
import { StatusPill } from "../components/ui/StatusPill";
import { TerminalButton } from "../components/ui/TerminalButton";
import {
  mockPolyAlphaEvidencePacks,
  mockPolyAlphaLinks,
  mockPolyAlphaMarketSnapshots,
  mockPolyAlphaOpportunities,
  mockTerminalSnapshot
} from "../data/mockTerminalData";

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function formatPercent(value: number) {
  return `${value}%`;
}

function formatLinkConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

const COCKPIT_HANDOFF_STORAGE_KEY = "poly-alpha-cockpit-handoffs";

type CockpitHandoff = {
  opportunityId: string;
  venueMarketId: string;
  venueContractId: string;
  outcomeId: string;
  title: string;
  createdAt: string;
};

function isCockpitHandoff(value: unknown): value is CockpitHandoff {
  return (
    value !== null &&
    typeof value === "object" &&
    "opportunityId" in value &&
    "venueMarketId" in value &&
    typeof value.opportunityId === "string" &&
    typeof value.venueMarketId === "string"
  );
}

function readCockpitHandoffs(): CockpitHandoff[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(COCKPIT_HANDOFF_STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter(isCockpitHandoff) : [];
  } catch {
    return [];
  }
}

function writeCockpitHandoffs(handoffs: CockpitHandoff[]) {
  window.localStorage.setItem(COCKPIT_HANDOFF_STORAGE_KEY, JSON.stringify(handoffs));
}

function upsertCockpitHandoff(handoffs: CockpitHandoff[], nextHandoff: CockpitHandoff) {
  return [
    nextHandoff,
    ...handoffs.filter((handoff) => handoff.opportunityId !== nextHandoff.opportunityId)
  ];
}

function buildOrderBook(selectedMarketId: string, baseBook: OrderBookSnapshot): OrderBookSnapshot {
  return {
    ...baseBook,
    marketId: selectedMarketId
  };
}

type PolyAlphaMarketRow = {
  opportunity: PolyAlphaOpportunity;
  links: PolyAlphaEventMarketLink[];
  evidence?: PolyAlphaEvidencePack;
  snapshot?: PolyAlphaMarketSnapshot;
};

function matchesPolyAlphaMarketIdentity(
  opportunity: PolyAlphaOpportunity,
  candidate: Pick<PolyAlphaEventMarketLink | PolyAlphaMarketSnapshot, "venueMarketId" | "venueContractId" | "outcomeId">
) {
  const opportunityIdentity = [
    opportunity.venueMarketId,
    opportunity.venueContractId,
    opportunity.outcomeId
  ];
  const candidateIdentity = [candidate.venueMarketId, candidate.venueContractId, candidate.outcomeId];

  return (
    opportunityIdentity.every((value) => value !== "") &&
    candidateIdentity.every((value) => value !== "") &&
    candidate.venueMarketId === opportunity.venueMarketId &&
    candidate.venueContractId === opportunity.venueContractId &&
    candidate.outcomeId === opportunity.outcomeId
  );
}

export function MarketsPage() {
  const [snapshot, setSnapshot] = useState<TerminalStatus>(mockTerminalSnapshot);
  const [polyAlphaOpportunities, setPolyAlphaOpportunities] = useState<PolyAlphaOpportunity[]>(mockPolyAlphaOpportunities);
  const [polyAlphaLinks, setPolyAlphaLinks] = useState<PolyAlphaEventMarketLink[]>(mockPolyAlphaLinks);
  const [polyAlphaEvidencePacks, setPolyAlphaEvidencePacks] =
    useState<PolyAlphaEvidencePack[]>(mockPolyAlphaEvidencePacks);
  const [polyAlphaMarketSnapshots, setPolyAlphaMarketSnapshots] =
    useState<PolyAlphaMarketSnapshot[]>(mockPolyAlphaMarketSnapshots);
  const [selectedMarketId, setSelectedMarketId] = useState(mockTerminalSnapshot.markets[0]?.id ?? "");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchFilter, setSearchFilter] = useState("");
  const [cockpitHandoffOpportunityIds, setCockpitHandoffOpportunityIds] = useState<string[]>(() =>
    readCockpitHandoffs().map((handoff) => handoff.opportunityId)
  );
  const [lastCockpitHandoffMarketId, setLastCockpitHandoffMarketId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    Promise.all([
      getTerminalSnapshot(),
      fetchPolyAlphaOpportunities(),
      fetchPolyAlphaLinks(),
      fetchPolyAlphaEvidencePacks(),
      fetchPolyAlphaMarketSnapshots()
    ])
      .then(([nextSnapshot, nextOpportunities, nextLinks, nextEvidencePacks, nextMarketSnapshots]) => {
        if (!isMounted) {
          return;
        }

        setSnapshot(nextSnapshot);
        setPolyAlphaOpportunities(nextOpportunities);
        setPolyAlphaLinks(nextLinks);
        setPolyAlphaEvidencePacks(nextEvidencePacks);
        setPolyAlphaMarketSnapshots(nextMarketSnapshots);
        if (nextSnapshot.markets[0]) {
          setSelectedMarketId((current) => current || nextSnapshot.markets[0].id);
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

  const categories = useMemo(
    () => ["all", ...new Set(snapshot.markets.map((market) => market.category))],
    [snapshot.markets]
  );

  const filteredMarkets = useMemo(
    () =>
      snapshot.markets.filter((market) => {
        const matchesCategory = categoryFilter === "all" || market.category === categoryFilter;
        const searchTerm = searchFilter.trim().toLowerCase();
        const matchesSearch =
          searchTerm === "" ||
          market.id.toLowerCase().includes(searchTerm) ||
          market.question.toLowerCase().includes(searchTerm);

        return matchesCategory && matchesSearch;
      }),
    [categoryFilter, searchFilter, snapshot.markets]
  );

  const selectedMarket = useMemo(
    () =>
      filteredMarkets.find((market) => market.id === selectedMarketId) ??
      snapshot.markets.find((market) => market.id === selectedMarketId) ??
      filteredMarkets[0] ??
      snapshot.markets[0],
    [filteredMarkets, selectedMarketId, snapshot.markets]
  );

  const polyAlphaRows = useMemo<PolyAlphaMarketRow[]>(
    () =>
      polyAlphaOpportunities.map((opportunity) => ({
        opportunity,
        links: polyAlphaLinks.filter((link) => matchesPolyAlphaMarketIdentity(opportunity, link)),
        evidence: polyAlphaEvidencePacks.find((pack) => pack.opportunityId === opportunity.id),
        snapshot: polyAlphaMarketSnapshots.find((marketSnapshot) =>
          matchesPolyAlphaMarketIdentity(opportunity, marketSnapshot)
        )
      })),
    [polyAlphaEvidencePacks, polyAlphaLinks, polyAlphaMarketSnapshots, polyAlphaOpportunities]
  );
  const cockpitHandoffSet = useMemo(
    () => new Set(cockpitHandoffOpportunityIds),
    [cockpitHandoffOpportunityIds]
  );

  function handleCockpitHandoff(opportunity: PolyAlphaOpportunity) {
    const handoff: CockpitHandoff = {
      opportunityId: opportunity.id,
      venueMarketId: opportunity.venueMarketId,
      venueContractId: opportunity.venueContractId,
      outcomeId: opportunity.outcomeId,
      title: opportunity.title,
      createdAt: new Date().toISOString()
    };
    writeCockpitHandoffs(upsertCockpitHandoff(readCockpitHandoffs(), handoff));
    setCockpitHandoffOpportunityIds((current) =>
      current.includes(opportunity.id) ? current : [...current, opportunity.id]
    );
    setLastCockpitHandoffMarketId(opportunity.venueMarketId);
    window.dispatchEvent(
      new CustomEvent("poly-alpha-cockpit-handoff", {
        detail: handoff
      })
    );
  }

  const candidateColumns: Array<DenseDataTableColumn<MarketCandidate>> = [
    {
      key: "select",
      header: "",
      render: (row) => (
        <TerminalButton
          aria-label={`Select ${row.id}`}
          tone={selectedMarket?.id === row.id ? "accent" : "default"}
          onClick={() => setSelectedMarketId(row.id)}
        >
          {selectedMarket?.id === row.id ? "Selected" : "Select"}
        </TerminalButton>
      )
    },
    {
      key: "question",
      header: "Question",
      render: (row) => row.question
    },
    {
      key: "category",
      header: "Category",
      render: (row) => row.category
    },
    {
      key: "probability",
      header: "Prob",
      align: "right",
      render: (row) => formatPercent(row.probability)
    },
    {
      key: "liquidity",
      header: "Liquidity",
      align: "right",
      render: (row) => formatUsd(row.liquidityUsd)
    }
  ];

  const polyAlphaColumns: Array<DenseDataTableColumn<PolyAlphaMarketRow>> = [
    {
      key: "market",
      header: "Market",
      render: (row) => row.opportunity.venueMarketId
    },
    {
      key: "linked",
      header: "Linked events",
      render: (row) => `${new Set(row.links.map((link) => link.eventId)).size} linked event`
    },
    {
      key: "evidence",
      header: "Latest evidence",
      render: (row) => row.evidence?.latestObservedAt ?? ""
    },
    {
      key: "probability",
      header: "Market vs estimate",
      render: (row) =>
        `${formatPercent(row.opportunity.marketProbability)} vs ${formatPercent(row.opportunity.estimatedProbability)}`
    },
    {
      key: "liquidity",
      header: "Liquidity",
      align: "right",
      render: (row) => (row.snapshot ? formatUsd(row.snapshot.liquidity) : "")
    },
    {
      key: "spread",
      header: "Spread",
      align: "right",
      render: (row) => row.snapshot?.spread.toFixed(2) ?? ""
    },
    {
      key: "freshness",
      header: "Order book freshness",
      render: (row) => row.snapshot?.fetchedAt ?? ""
    },
    {
      key: "confidence",
      header: "Link confidence",
      render: (row) =>
        row.links.length > 0 ? formatLinkConfidence(Math.max(...row.links.map((link) => link.linkConfidence))) : ""
    },
    {
      key: "handoff",
      header: "Handoff",
      render: (row) => (cockpitHandoffSet.has(row.opportunity.id) ? "queued for cockpit" : "")
    },
    {
      key: "action",
      header: "Action",
      render: (row) => (
        <TerminalButton
          aria-label={`Send ${row.opportunity.venueMarketId} to research/Cockpit`}
          onClick={() => handleCockpitHandoff(row.opportunity)}
        >
          Research/Cockpit
        </TerminalButton>
      )
    }
  ];

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Advisory market readout</p>
          <h1>Markets</h1>
        </div>
        <div className="status-row">
          <StatusPill label={`${snapshot.markets.length} candidates`} tone="warn" />
          {snapshot.status.source === "mock" ? <StatusPill label="mock fallback" tone="mock" /> : null}
        </div>
      </div>

      <div className="filter-row" aria-label="Market filters">
        <label>
          Category
          <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category === "all" ? "All categories" : category}
              </option>
            ))}
          </select>
        </label>
        <label>
          Search
          <input
            value={searchFilter}
            onChange={(event) => setSearchFilter(event.target.value)}
            placeholder="market id or question"
          />
        </label>
      </div>

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Candidate queue</h2>
          <DenseDataTable
            caption="Market candidates"
            columns={candidateColumns}
            rows={filteredMarkets}
            getRowKey={(row) => row.id}
            emptyTitle="No candidate markets"
            emptyDescription="No paper-only market candidates match the current filters."
          />
        </div>

        <div className="page-section">
          <h2>Selected market</h2>
          {selectedMarket ? (
            <div className="detail-stack">
              <div className="detail-grid">
                <div>
                  <span className="detail-label">Market id</span>
                  <strong>{selectedMarket.id}</strong>
                </div>
                <div>
                  <span className="detail-label">Category</span>
                  <strong>{selectedMarket.category}</strong>
                </div>
                <div>
                  <span className="detail-label">Probability</span>
                  <strong>{formatPercent(selectedMarket.probability)}</strong>
                </div>
                <div>
                  <span className="detail-label">Spread</span>
                  <strong>{selectedMarket.spreadBps} bps</strong>
                </div>
              </div>
              <p className="detail-copy">Question: {selectedMarket.question}</p>
              <ProbabilityChart
                label={`${selectedMarket.id} probability history`}
                data={snapshot.probabilityHistory}
              />
              <OrderBookSummary book={buildOrderBook(selectedMarket.id, snapshot.orderBook)} />
            </div>
          ) : null}
        </div>
      </div>

      <div className="page-section">
        {lastCockpitHandoffMarketId ? (
          <p className="page-warning">Sent to Cockpit: {lastCockpitHandoffMarketId}</p>
        ) : null}
        <h2>Poly Alpha market links</h2>
        <DenseDataTable
          caption="Poly Alpha market links"
          columns={polyAlphaColumns}
          rows={polyAlphaRows}
          getRowKey={(row) => row.opportunity.id}
          emptyTitle="No Poly Alpha market links"
          emptyDescription="No linked evidence or market snapshots are available."
        />
      </div>
    </section>
  );
}
