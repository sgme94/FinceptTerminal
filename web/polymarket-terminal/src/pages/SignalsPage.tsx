import { useEffect, useMemo, useState } from "react";
import {
  buildPolyAlphaSignalFilters,
  fetchPolyAlphaPromotions,
  fetchPolyAlphaShadowSignals,
  fetchPolyAlphaValidations,
  getSkips,
  getTerminalSnapshot
} from "../api/client";
import type {
  PolyAlphaPromotionDecision,
  PolyAlphaShadowSignal,
  PolyAlphaValidationResult,
  SignalRow,
  SkipRow,
  TerminalStatus
} from "../api/types";
import { DenseDataTable, type DenseDataTableColumn } from "../components/ui/DenseDataTable";
import { StatusPill } from "../components/ui/StatusPill";
import { TerminalButton } from "../components/ui/TerminalButton";
import {
  mockPolyAlphaPromotionDecisions,
  mockPolyAlphaShadowSignals,
  mockPolyAlphaValidationResults,
  mockSkips,
  mockTerminalSnapshot
} from "../data/mockTerminalData";

function formatBps(value: number) {
  return `${value} bps`;
}

function formatPercent(value: number) {
  return `${value}%`;
}

function formatDecimal(value: number) {
  return value.toFixed(2);
}

function numericFeatureEntries(features?: Record<string, number>): Array<[string, number]> {
  if (!features) {
    return [];
  }

  return Object.entries(features).filter(
    (entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1])
  );
}

type PolyAlphaSignalRow = PolyAlphaShadowSignal & {
  validation?: PolyAlphaValidationResult;
  promotion?: PolyAlphaPromotionDecision;
};
type ShadowStatusFilter = "all" | PolyAlphaShadowSignal["status"];
type PromotionDecisionFilter = "all" | PolyAlphaPromotionDecision["decision"];

export function SignalsPage() {
  const [snapshot, setSnapshot] = useState<TerminalStatus>(mockTerminalSnapshot);
  const [skips, setSkips] = useState<SkipRow[]>(mockSkips);
  const [polyAlphaShadowSignals, setPolyAlphaShadowSignals] =
    useState<PolyAlphaShadowSignal[]>(mockPolyAlphaShadowSignals);
  const [polyAlphaValidations, setPolyAlphaValidations] =
    useState<PolyAlphaValidationResult[]>(mockPolyAlphaValidationResults);
  const [polyAlphaPromotions, setPolyAlphaPromotions] =
    useState<PolyAlphaPromotionDecision[]>(mockPolyAlphaPromotionDecisions);
  const [shadowStatusFilter, setShadowStatusFilter] = useState<ShadowStatusFilter>("all");
  const [promotionDecisionFilter, setPromotionDecisionFilter] = useState<PromotionDecisionFilter>("all");
  const [selectedSignalId, setSelectedSignalId] = useState(mockTerminalSnapshot.signals[0]?.id ?? "");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    Promise.all([
      getTerminalSnapshot(),
      getSkips(),
      fetchPolyAlphaShadowSignals(),
      fetchPolyAlphaValidations(),
      fetchPolyAlphaPromotions()
    ])
      .then(([nextSnapshot, nextSkips, nextShadowSignals, nextValidations, nextPromotions]) => {
        if (!isMounted) {
          return;
        }

        setSnapshot(nextSnapshot);
        setSkips(nextSkips);
        setPolyAlphaShadowSignals(nextShadowSignals);
        setPolyAlphaValidations(nextValidations);
        setPolyAlphaPromotions(nextPromotions);
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
  const validationBySignal = useMemo(
    () => new Map(polyAlphaValidations.map((validation) => [validation.shadowSignalId, validation])),
    [polyAlphaValidations]
  );
  const promotionBySignal = useMemo(
    () => new Map(polyAlphaPromotions.map((promotion) => [promotion.shadowSignalId, promotion])),
    [polyAlphaPromotions]
  );
  const polyAlphaRows = useMemo<PolyAlphaSignalRow[]>(
    () =>
      polyAlphaShadowSignals.map((signal) => ({
        ...signal,
        validation: validationBySignal.get(signal.id),
        promotion: promotionBySignal.get(signal.id)
      })),
    [polyAlphaShadowSignals, promotionBySignal, validationBySignal]
  );
  const polyAlphaFilters = useMemo(
    () =>
      buildPolyAlphaSignalFilters({
        shadowStatuses: ["shadow", "validated", "promoted", "rejected", "expired", "watch"],
        promotionDecisions: ["watch", "promote", "reject"]
      }),
    []
  );
  const filteredPolyAlphaRows = useMemo(
    () =>
      polyAlphaRows.filter((row) => {
        const matchesShadowStatus = shadowStatusFilter === "all" || row.status === shadowStatusFilter;
        const matchesPromotionDecision =
          promotionDecisionFilter === "all" || row.promotion?.decision === promotionDecisionFilter;

        return matchesShadowStatus && matchesPromotionDecision;
      }),
    [polyAlphaRows, promotionDecisionFilter, shadowStatusFilter]
  );

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

  const polyAlphaColumns: Array<DenseDataTableColumn<PolyAlphaSignalRow>> = [
    {
      key: "signal",
      header: "Signal",
      render: (row) => row.id
    },
    {
      key: "strategy",
      header: "Strategy version",
      render: (row) => row.strategyVersionId
    },
    {
      key: "status",
      header: "Opportunity status",
      render: (row) => <StatusPill label={row.status} tone={row.status === "validated" ? "ok" : "warn"} />
    },
    {
      key: "decision",
      header: "Promotion decision",
      render: (row) => row.promotion?.decision ?? ""
    },
    {
      key: "clv",
      header: "CLV",
      align: "right",
      render: (row) => (row.validation ? `CLV ${formatDecimal(row.validation.closingLineValue)}` : "")
    },
    {
      key: "brier",
      header: "Brier",
      align: "right",
      render: (row) => (row.validation ? `Brier ${formatDecimal(row.validation.brierScore)}` : "")
    },
    {
      key: "calibration",
      header: "Calibration",
      align: "right",
      render: (row) => (row.validation ? `Calibration ${formatDecimal(row.validation.calibrationError)}` : "")
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

      <div className="page-grid terminal-page-grid-compact">
        <div className="page-section">
          <h2>Poly Alpha shadow signals</h2>
          <DenseDataTable
            caption="Poly Alpha shadow signals"
            columns={polyAlphaColumns}
            rows={filteredPolyAlphaRows}
            getRowKey={(row) => row.id}
            emptyTitle="No Poly Alpha shadow signals"
            emptyDescription="No shadow signals are available."
          />
        </div>

        <div className="detail-stack">
          <div className="page-section">
            <h2>Shadow status filters</h2>
            <div className="detail-badges" aria-label="Shadow status filters">
              <TerminalButton
                aria-label="Filter shadow status all"
                tone={shadowStatusFilter === "all" ? "accent" : "default"}
                onClick={() => setShadowStatusFilter("all")}
              >
                all
              </TerminalButton>
              {polyAlphaFilters.shadowStatuses.map((status) => (
                <TerminalButton
                  key={status}
                  aria-label={`Filter shadow status ${status}`}
                  tone={shadowStatusFilter === status ? "accent" : "default"}
                  onClick={() => setShadowStatusFilter(status)}
                >
                  {status}
                </TerminalButton>
              ))}
            </div>
          </div>

          <div className="page-section">
            <h2>Promotion decision filters</h2>
            <div className="detail-badges" aria-label="Promotion decision filters">
              <TerminalButton
                aria-label="Filter promotion decision all"
                tone={promotionDecisionFilter === "all" ? "accent" : "default"}
                onClick={() => setPromotionDecisionFilter("all")}
              >
                all
              </TerminalButton>
              {polyAlphaFilters.promotionDecisions.map((decision) => (
                <TerminalButton
                  key={decision}
                  aria-label={`Filter promotion decision ${decision}`}
                  tone={promotionDecisionFilter === decision ? "accent" : "default"}
                  onClick={() => setPromotionDecisionFilter(decision)}
                >
                  {decision}
                </TerminalButton>
              ))}
            </div>
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
