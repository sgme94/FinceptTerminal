import { useEffect, useMemo, useState } from "react";
import { getSkips, getTerminalSnapshot } from "../api/client";
import type { SignalRow, SkipRow, TerminalStatus } from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";
import { mockSkips, mockTerminalSnapshot } from "../data/mockTerminalData";

function formatBps(value: number) {
  return `${value} bps`;
}

function formatPercent(value: number) {
  return `${value}%`;
}

function numericFeatureEntries(features?: Record<string, number>): Array<[string, number]> {
  if (!features) {
    return [];
  }

  return Object.entries(features).filter(
    (entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1])
  );
}

export function SignalsPage() {
  const [snapshot, setSnapshot] = useState<TerminalStatus>(mockTerminalSnapshot);
  const [skips, setSkips] = useState<SkipRow[]>(mockSkips);
  const [selectedSignalId, setSelectedSignalId] = useState(mockTerminalSnapshot.signals[0]?.id ?? "");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    Promise.all([getTerminalSnapshot(), getSkips()])
      .then(([nextSnapshot, nextSkips]) => {
        if (!isMounted) {
          return;
        }

        setSnapshot(nextSnapshot);
        setSkips(nextSkips);
        if (nextSnapshot.signals[0]) {
          setSelectedSignalId((current) => current || nextSnapshot.signals[0].id);
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

  const selectedSignal = useMemo(
    () =>
      snapshot.signals.find((signal) => signal.id === selectedSignalId) ??
      snapshot.signals[0],
    [selectedSignalId, snapshot.signals]
  );
  const featureEntries = useMemo(() => numericFeatureEntries(selectedSignal?.features), [selectedSignal]);

  const signalColumns: Array<DenseDataTableColumn<SignalRow>> = [
    {
      key: "label",
      header: "Signal",
      render: (row) => (
        <button
          type="button"
          className="table-link-button"
          onClick={() => setSelectedSignalId(row.id)}
        >
          {row.label}
        </button>
      )
    },
    {
      key: "edge",
      header: "Edge",
      align: "right",
      render: (row) => formatBps(row.edgeBps)
    },
    {
      key: "confidence",
      header: "Confidence",
      align: "right",
      render: (row) => formatPercent(row.confidence)
    },
    {
      key: "reason",
      header: "Reason",
      render: (row) => row.reason ?? ""
    },
  ];

  const skipColumns: Array<DenseDataTableColumn<SkipRow>> = [
    {
      key: "reason",
      header: "Reason",
      render: (row) => row.reason
    },
    {
      key: "market",
      header: "Market",
      render: (row) => row.marketId
    },
    {
      key: "detail",
      header: "Detail",
      render: (row) => row.detail
    }
  ];

  return (
    <section className="workspace-panel page-stack" aria-busy={isLoading}>
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Advisory signal review</p>
          <h1>Signals</h1>
        </div>
        <div className="status-row">
          <StatusPill label="advisory only" tone="warn" />
          {snapshot.status.source === "mock" ? <StatusPill label="mock fallback" tone="mock" /> : null}
        </div>
      </div>

      <p className="page-warning">
        Signals are read-only trade advice. No order execution or live routing is exposed here.
      </p>

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Signal queue</h2>
          <DenseDataTable
            caption="Signal table"
            columns={signalColumns}
            rows={snapshot.signals}
            getRowKey={(row) => row.id}
            emptyTitle="No signals"
            emptyDescription="No advisory signals are available."
          />
        </div>

        <div className="detail-stack">
          <div className="page-section">
            <h2>Feature contribution</h2>
            <div className="stack-list">
              {featureEntries.length > 0
                ? featureEntries.map(([feature, contribution]) => (
                    <div key={feature} className="detail-row">
                      <span>{feature}</span>
                      <strong>{contribution.toFixed(2)}</strong>
                    </div>
                  ))
                : <p className="workspace-kicker">No feature contribution data.</p>}
            </div>
          </div>

          <div className="page-section">
            <h2>Advisory evidence</h2>
            <div className="stack-list">
              {selectedSignal?.evidence?.map((item) => (
                <div key={item} className="detail-row">
                  <span>{item}</span>
                </div>
              )) ?? <p className="workspace-kicker">No advisory evidence rows.</p>}
            </div>
            {selectedSignal?.freshnessLabel ? (
              <div className="detail-badges">
                <StatusPill label={selectedSignal.freshnessLabel} tone="warn" />
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="page-section">
        <h2>Skip review</h2>
        <DenseDataTable
          caption="Skip rows"
          columns={skipColumns}
          rows={skips}
          getRowKey={(row) => row.id}
          emptyTitle="No skip rows"
          emptyDescription="No skip reasons have been recorded."
        />
      </div>
    </section>
  );
}
