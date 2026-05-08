import { useEffect, useState } from "react";
import { fetchPolyAlphaEvidencePacks, fetchPolyAlphaScanRuns } from "../api/client";
import type { PolyAlphaEvidencePack, PolyAlphaScanRun } from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";
import { mockPolyAlphaEvidencePacks, mockPolyAlphaScanRuns } from "../data/mockTerminalData";

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

const evidenceColumns: Array<DenseDataTableColumn<PolyAlphaEvidencePack>> = [
  {
    key: "pack",
    header: "Evidence pack",
    render: (row) => row.id
  },
  {
    key: "opportunity",
    header: "Opportunity",
    render: (row) => row.opportunityId
  },
  {
    key: "latest",
    header: "Latest evidence",
    render: (row) => row.latestObservedAt
  },
  {
    key: "sources",
    header: "Sources",
    render: (row) => `${row.documentIds.length} docs / ${row.snapshotIds.length} snapshots`
  }
];

const scanColumns: Array<DenseDataTableColumn<PolyAlphaScanRun>> = [
  {
    key: "scan",
    header: "Scan run",
    render: (row) => row.id
  },
  {
    key: "status",
    header: "Status",
    render: (row) => row.status
  },
  {
    key: "trigger",
    header: "Trigger",
    render: (row) => row.triggerType
  },
  {
    key: "counts",
    header: "Counts",
    render: (row) => `${row.scannedCount} scanned / ${row.createdOpportunityCount} opportunities`
  }
];

export function NewsPage() {
  const [evidencePacks, setEvidencePacks] = useState<PolyAlphaEvidencePack[]>(mockPolyAlphaEvidencePacks);
  const [scanRuns, setScanRuns] = useState<PolyAlphaScanRun[]>(mockPolyAlphaScanRuns);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchPolyAlphaEvidencePacks(), fetchPolyAlphaScanRuns()])
      .then(([nextEvidencePacks, nextScanRuns]) => {
        if (!isMounted) {
          return;
        }

        setEvidencePacks(nextEvidencePacks);
        setScanRuns(nextScanRuns);
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

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
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

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Evidence packs</h2>
          <DenseDataTable
            caption="Evidence packs"
            columns={evidenceColumns}
            rows={evidencePacks}
            getRowKey={(row) => row.id}
            emptyTitle="No evidence packs"
            emptyDescription="No Poly Alpha evidence packs are available."
          />
        </div>

        <div className="page-section">
          <h2>Scan runs</h2>
          <DenseDataTable
            caption="Scan runs"
            columns={scanColumns}
            rows={scanRuns}
            getRowKey={(row) => row.id}
            emptyTitle="No scan runs"
            emptyDescription="No Poly Alpha scan runs are available."
          />
        </div>
      </div>
    </section>
  );
}
