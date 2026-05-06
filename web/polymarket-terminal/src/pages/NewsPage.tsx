import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";

type NewsItem = {
  id: string;
  headline: string;
  source: string;
  freshness: string;
  impact: "High impact" | "Medium impact" | "Low impact";
  marketHint: string;
};

const newsItems: NewsItem[] = [
  {
    id: "news-polymarket-fees",
    headline: "Polymarket liquidity note highlights macro and crypto depth",
    source: "Polymarket blog",
    freshness: "fresh 4m",
    impact: "High impact",
    marketHint: "Macro, crypto"
  },
  {
    id: "news-fed-speakers",
    headline: "Fed speaker calendar pulls rate-cut markets into focus",
    source: "Public calendar",
    freshness: "fresh 18m",
    impact: "Medium impact",
    marketHint: "Rates"
  },
  {
    id: "news-election-filings",
    headline: "Election filing window closes with no candidate surprise",
    source: "Newswire mock",
    freshness: "fresh 42m",
    impact: "Low impact",
    marketHint: "Politics"
  }
];

const columns: Array<DenseDataTableColumn<NewsItem>> = [
  {
    key: "headline",
    header: "Headline",
    render: (row) => row.headline
  },
  {
    key: "impact",
    header: "Impact",
    render: (row) => (
      <StatusPill
        label={row.impact}
        tone={row.impact === "High impact" ? "danger" : row.impact === "Medium impact" ? "warn" : "neutral"}
      />
    )
  },
  {
    key: "source",
    header: "Source",
    render: (row) => row.source
  },
  {
    key: "freshness",
    header: "Freshness",
    render: (row) => row.freshness
  },
  {
    key: "marketHint",
    header: "Market hint",
    render: (row) => row.marketHint
  }
];

export function NewsPage() {
  return (
    <section className="workspace-panel page-stack">
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Advisory read-only feed</p>
          <h1>News</h1>
        </div>
        <div className="status-row" aria-label="News mode">
          <StatusPill label="mock feed" tone="mock" />
          <StatusPill label="no trade execution" tone="ok" />
        </div>
      </div>

      <div className="page-section">
        <h2>Live-style mock feed</h2>
        <DenseDataTable
          caption="Mock news feed"
          columns={columns}
          rows={newsItems}
          getRowKey={(row) => row.id}
          emptyTitle="No news items"
          emptyDescription="The advisory feed has no items to display."
        />
      </div>
    </section>
  );
}
