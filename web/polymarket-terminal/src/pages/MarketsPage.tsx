import { useEffect, useMemo, useState } from "react";
import { getTerminalSnapshot } from "../api/client";
import type { MarketCandidate, OrderBookSnapshot, TerminalStatus } from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { OrderBookSummary } from "../components/ui/OrderBookSummary";
import { ProbabilityChart } from "../components/ui/ProbabilityChart";
import { StatusPill } from "../components/ui/StatusPill";
import { TerminalButton } from "../components/ui/TerminalButton";
import { mockTerminalSnapshot } from "../data/mockTerminalData";

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

function buildOrderBook(selectedMarketId: string, baseBook: OrderBookSnapshot): OrderBookSnapshot {
  return {
    ...baseBook,
    marketId: selectedMarketId
  };
}

export function MarketsPage() {
  const [snapshot, setSnapshot] = useState<TerminalStatus>(mockTerminalSnapshot);
  const [selectedMarketId, setSelectedMarketId] = useState(mockTerminalSnapshot.markets[0]?.id ?? "");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchFilter, setSearchFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    getTerminalSnapshot()
      .then((nextSnapshot) => {
        if (!isMounted) {
          return;
        }

        setSnapshot(nextSnapshot);
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
    </section>
  );
}
