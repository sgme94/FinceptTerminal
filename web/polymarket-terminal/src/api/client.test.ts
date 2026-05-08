import { afterEach, describe, expect, it, vi } from "vitest";
import {
  approveTradeProposal,
  buildPolyAlphaSignalFilters,
  fetchPolyAlphaCockpit,
  fetchPolyAlphaDocuments,
  fetchPolyAlphaEvents,
  fetchPolyAlphaFindings,
  fetchPolyAlphaLinks,
  fetchPolyAlphaMarketSnapshots,
  fetchPolyAlphaOpportunities,
  fetchPolyAlphaResearchRuns,
  fetchPolyAlphaScanResults,
  fetchPolyAlphaScanRuns,
  getAuditEvents,
  getBotStatus,
  getCandidates,
  getPaperPositions,
  getPaperTrades,
  getSignals,
  getSkips,
  getTerminalSnapshot,
  getTradeProposals,
  rejectTradeProposal,
  triggerKillSwitch
} from "./client";

describe("terminal api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches bot status from the backend api", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          mode: "paper",
          live_enabled: true,
          approval_mode: "manual",
          status: "running",
          healthy: true,
          db_path: "C:/data/polymarket.db"
        })
    });
    vi.stubGlobal("fetch", fetchMock);

    const status = await getBotStatus();

    expect.soft(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/bot/status");
    expect.soft(status.source).toBe("api");
    expect.soft(status).toEqual(
      expect.objectContaining({
        deploymentId: "default",
        state: "online",
        mode: "paper",
        lastHeartbeat: "",
        activeMarkets: 0,
        pendingProposals: 0,
        exposureUsd: 0,
        liveEnabled: true,
        approvalMode: "manual",
        apiStatus: "running",
        healthy: true,
        dbPath: "C:/data/polymarket.db"
      })
    );
  });

  it("fetches audit events for a deployment from the backend api", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          events: [
            {
              event_id: "audit-1",
              deployment_id: "dep-1",
              strategy_id: "strategy-1",
              actor_type: "operator",
              actor_id: "user-1",
              action: "approve",
              entity_type: "proposal",
              entity_id: "proposal-1",
              before: { status: "proposed" },
              after: { status: "approved" },
              result: "success",
              reason: "Risk limits passed",
              request_id: "request-1",
              created_at: "2026-05-06T01:00:00.000Z"
            }
          ]
        })
    });
    vi.stubGlobal("fetch", fetchMock);

    const events = await getAuditEvents("dep-1");

    expect.soft(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8765/api/audit?deployment_id=dep-1"
    );
    expect.soft(events).toEqual([
      expect.objectContaining({
        id: "audit-1",
        deploymentId: "dep-1",
        strategyId: "strategy-1",
        actor: "user",
        actorType: "operator",
        actorId: "user-1",
        action: "approve",
        entityType: "proposal",
        entityId: "proposal-1",
        level: "info",
        message: "approve success: Risk limits passed",
        result: "success",
        reason: "Risk limits passed",
        requestId: "request-1",
        createdAt: "2026-05-06T01:00:00.000Z",
        source: "api"
      })
    ]);
  });

  it("fetches trade proposals for a deployment from the backend api", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          proposals: [
            {
              proposal_id: "proposal-1",
              deployment_id: "dep-1",
              strategy_id: "strategy-1",
              condition_id: "condition-1",
              asset_id: "asset-1",
              market_id: "market-1",
              side: "buy",
              price: 0.58,
              size: 25,
              status: "proposed",
              reason: "Positive edge",
              created_at: "2026-05-06T01:00:00.000Z"
            }
          ]
        })
    });
    vi.stubGlobal("fetch", fetchMock);

    const proposals = await getTradeProposals("dep-1");

    expect.soft(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8765/api/proposals?deployment_id=dep-1"
    );
    expect.soft(proposals).toEqual([
      expect.objectContaining({
        id: "proposal-1",
        deploymentId: "dep-1",
        strategyId: "strategy-1",
        conditionId: "condition-1",
        assetId: "asset-1",
        marketId: "market-1",
        side: "buy",
        outcome: "yes",
        price: 0.58,
        sizeUsd: 25,
        rationale: "Positive edge",
        status: "proposed",
        createdAt: "2026-05-06T01:00:00.000Z",
        source: "api"
      })
    ]);
  });

  it("preserves backend trade proposal lifecycle statuses", async () => {
    const statuses = [
      "proposed",
      "approved",
      "rejected",
      "expired",
      "cancelled",
      "filled",
      "failed"
    ];
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          proposals: statuses.map((status) => ({
            proposal_id: `proposal-${status}`,
            deployment_id: "dep-1",
            market_id: `market-${status}`,
            side: "buy",
            price: 0.5,
            size: 10,
            status,
            created_at: "2026-05-06T01:00:00.000Z"
          }))
        })
    });
    vi.stubGlobal("fetch", fetchMock);

    const proposals = await getTradeProposals("dep-1");

    expect(proposals.map((proposal) => proposal.status)).toEqual(statuses);
  });

  it("fetches candidates, signals, and skips for a deployment from read-only endpoints", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "http://localhost:8765/api/candidates?deployment_id=dep-1") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              candidates: [
                {
                  market_id: "market-1",
                  outcome: "yes",
                  price: 0.57,
                  volume: 1000,
                  liquidity: 250,
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      if (url === "http://localhost:8765/api/signals?deployment_id=dep-1") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              signals: [
                {
                  id: 7,
                  asset_id: "asset-1",
                  action: "buy",
                  estimated_probability: 0.62,
                  edge: 0.0118,
                  confidence: 0.64,
                  reason: "Fed implied path moved faster than market price.",
                  features: { "macro repricing": 0.42 },
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      if (url === "http://localhost:8765/api/skips?deployment_id=dep-1") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              skips: [
                {
                  id: 3,
                  market_id: "market-thin",
                  asset_id: "asset-thin",
                  reason: "liquidity_below_threshold",
                  detail: "liquidity 8 < 100",
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      return Promise.reject(new Error(`unexpected url ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCandidates("dep-1")).resolves.toEqual([
      expect.objectContaining({ id: "market-1", probability: 57, liquidityUsd: 250, source: "api" })
    ]);
    await expect(getSignals("dep-1")).resolves.toEqual([
      expect.objectContaining({
        id: "signal-7",
        marketId: "asset-1",
        edgeBps: 118,
        confidence: 64,
        reason: "Fed implied path moved faster than market price.",
        source: "api"
      })
    ]);
    await expect(getSkips("dep-1")).resolves.toEqual([
      expect.objectContaining({
        id: "skip-3",
        marketId: "market-thin",
        reason: "liquidity_below_threshold",
        source: "api"
      })
    ]);
  });

  it("fetches paper trades and positions for a deployment from read-only endpoints", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "http://localhost:8765/api/trades?deployment_id=dep-1") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              trades: [
                {
                  id: 9,
                  deployment_id: "dep-1",
                  asset_id: "asset-1",
                  side: "BUY",
                  size: 10,
                  price: 0.42,
                  realized_pnl: 0,
                  reason: "manual approval fill",
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      if (url === "http://localhost:8765/api/positions?deployment_id=dep-1") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              positions: [
                {
                  deployment_id: "dep-1",
                  asset_id: "asset-1",
                  size: 10,
                  avg_price: 0.42,
                  realized_pnl: 0,
                  updated_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      return Promise.reject(new Error(`unexpected url ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPaperTrades("dep-1")).resolves.toEqual([
      expect.objectContaining({
        id: "trade-9",
        assetId: "asset-1",
        side: "BUY",
        size: 10,
        price: 0.42,
        source: "api"
      })
    ]);
    await expect(getPaperPositions("dep-1")).resolves.toEqual([
      expect.objectContaining({
        id: "position-asset-1",
        assetId: "asset-1",
        size: 10,
        avgPrice: 0.42,
        exposureUsd: 4.2,
        source: "api"
      })
    ]);
  });

  it("drops nonnumeric signal features from backend api responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          signals: [
            {
              id: 8,
              asset_id: "asset-2",
              action: "buy",
              edge: 0.01,
              confidence: 0.5,
              features: { good: 0.42, bad: "x", empty: null },
              created_at: "2026-05-06T01:00:00.000Z"
            }
          ]
        })
    });
    vi.stubGlobal("fetch", fetchMock);

    const signals = await getSignals("dep-1");

    expect(signals[0].features).toEqual({ good: 0.42 });
  });

  it("posts proposal decisions and paper kill switch audit requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ accepted: true })
    });
    vi.stubGlobal("fetch", fetchMock);

    await approveTradeProposal("proposal-1", {
      deployment_id: "dep-1",
      strategy_id: "strat-1",
      actor_id: "reviewer",
      reason: "approved from test"
    });
    await rejectTradeProposal("proposal-1", {
      deployment_id: "dep-1",
      strategy_id: "strat-1",
      actor_id: "reviewer",
      reason: "rejected from test"
    });
    await triggerKillSwitch({
      deployment_id: "dep-1",
      strategy_id: "manual",
      actor_id: "reviewer",
      reason: "paper kill switch"
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8765/api/proposals/proposal-1/approve",
      expect.objectContaining({ method: "POST" })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8765/api/proposals/proposal-1/reject",
      expect.objectContaining({ method: "POST" })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8765/api/control/kill-switch",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("returns mock bot status when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const status = await getBotStatus();

    expect(status.source).toBe("mock");
    expect(status.stale).toBe(true);
    expect(status.mode).toBe("paper");
    expect(status.liveEnabled).toBe(false);
  });

  it("aggregates terminal snapshot from existing backend api endpoints", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "http://localhost:8765/api/bot/status") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              mode: "paper",
              live_enabled: true,
              approval_mode: "manual",
              status: "running",
              healthy: true,
              db_path: "C:/data/polymarket.db"
            })
        });
      }

      if (url === "http://localhost:8765/api/proposals?deployment_id=default") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              proposals: [
                {
                  proposal_id: "proposal-default",
                  deployment_id: "default",
                  market_id: "market-default",
                  side: "buy",
                  price: 0.61,
                  size: 40,
                  status: "proposed",
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      if (url === "http://localhost:8765/api/audit?deployment_id=default") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              events: [
                {
                  event_id: "audit-default",
                  deployment_id: "default",
                  actor_type: "system",
                  action: "propose",
                  result: "success",
                  created_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      return Promise.reject(new Error(`unexpected url ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    const snapshot = await getTerminalSnapshot();

    expect(fetchMock).not.toHaveBeenCalledWith("http://localhost:8765/terminal/snapshot");
    expect(fetchMock).not.toHaveBeenCalledWith("http://localhost:8765/api/terminal/snapshot");
    expect(snapshot.status.source).toBe("api");
    expect(snapshot.proposals).toEqual([
      expect.objectContaining({
        id: "proposal-default",
        status: "proposed",
        source: "api"
      })
    ]);
    expect(snapshot.auditEvents).toEqual([
      expect.objectContaining({
        id: "audit-default",
        source: "api"
      })
    ]);
    expect(snapshot.status.exposureUsd).toBe(0);
    expect(snapshot.markets.length).toBeGreaterThan(0);
    expect(snapshot.signals.length).toBeGreaterThan(0);
    expect(snapshot.riskLimits.length).toBeGreaterThan(0);
  });

  it("derives snapshot exposure and active markets from paper positions", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "http://localhost:8765/api/bot/status") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ mode: "paper", status: "running", healthy: true })
        });
      }

      if (url === "http://localhost:8765/api/positions?deployment_id=default") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              positions: [
                {
                  deployment_id: "default",
                  asset_id: "asset-1",
                  size: 10,
                  avg_price: 0.4,
                  realized_pnl: 1,
                  updated_at: "2026-05-06T01:00:00.000Z"
                },
                {
                  deployment_id: "default",
                  asset_id: "asset-2",
                  size: 5,
                  avg_price: 0.6,
                  realized_pnl: 0,
                  updated_at: "2026-05-06T01:00:00.000Z"
                }
              ]
            })
        });
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ proposals: [], trades: [], events: [], candidates: [], signals: [] })
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const snapshot = await getTerminalSnapshot();

    expect(snapshot.status.exposureUsd).toBe(7);
    expect(snapshot.status.activeMarkets).toBe(2);
  });

  it("fetches poly alpha resources from their backend api endpoints", async () => {
    const responseByUrl: Record<string, unknown> = {
      "http://localhost:8765/api/poly-alpha/opportunities": {
        items: [
          {
            opportunity_id: "opp-1",
            strategy_version_id: "strategy-v1",
            venue: "polymarket",
            venue_market_id: "market-1",
            venue_contract_id: "condition-1",
            outcome_id: "yes-token-1",
            title: "Fed path repricing",
            alpha_family: "macro",
            status: "watch",
            primary_reason: "late_information",
            market_probability: 0.58,
            estimated_probability: 0.64,
            edge: 0.06,
            confidence: 0.72,
            created_at: "2026-05-06T01:00:00.000Z",
            updated_at: "2026-05-06T01:05:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/scan-runs": {
        items: [
          {
            scan_run_id: "scan-1",
            trigger_type: "deterministic",
            strategy_version_id: "strategy-v1",
            config_version_id: "config-v1",
            source_set_version: "sources-v1",
            status: "completed",
            started_at: "2026-05-06T01:00:00.000Z",
            completed_at: "2026-05-06T01:03:00.000Z",
            scanned_count: 12,
            ignored_count: 8,
            watch_count: 3,
            created_opportunity_count: 1,
            error_message: "",
            created_at: "2026-05-06T01:00:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/scan-results": {
        items: [
          {
            scan_result_id: "scan-result-1",
            scan_run_id: "scan-1",
            strategy_version_id: "strategy-v1",
            venue: "polymarket",
            venue_market_id: "market-1",
            venue_contract_id: "condition-1",
            outcome_id: "yes-token-1",
            decision: "watch",
            reason: "Late information changed the price anchor.",
            source_snapshot_ids: ["snapshot-1"],
            source_document_ids: ["doc-1"],
            created_opportunity_id: "opp-1",
            observed_at: "2026-05-06T00:58:00.000Z",
            created_at: "2026-05-06T01:03:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/market-snapshots": {
        items: [
          {
            snapshot_id: "snapshot-1",
            venue: "polymarket",
            venue_market_id: "market-1",
            venue_contract_id: "condition-1",
            outcome_id: "yes-token-1",
            adapter_metadata: { market_slug: "fed-june" },
            source_api: "clob",
            observed_at: "2026-05-06T00:58:00.000Z",
            fetched_at: "2026-05-06T00:59:00.000Z",
            payload_hash: "snapshot-hash-1",
            best_bid: 0.57,
            best_ask: 0.59,
            spread: 0.02,
            top_bid_depth: 820,
            top_ask_depth: 760,
            mid_price: 0.58,
            last_trade_price: 0.575,
            liquidity: 126000,
            volume: 842000,
            raw_payload: { market_id: "market-1" },
            created_at: "2026-05-06T01:00:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/documents": {
        items: [
          {
            document_id: "doc-1",
            source_type: "official",
            source_name: "Federal Reserve",
            title: "FOMC calendar",
            url: "https://example.com/fomc",
            api_endpoint: "",
            market_id: "",
            venue: "polymarket",
            venue_market_id: "market-1",
            venue_contract_id: "condition-1",
            outcome_id: "yes-token-1",
            asset_symbol: "FEDFUNDS",
            topic: "rates",
            published_at: "2026-05-06T00:00:00.000Z",
            fetched_at: "2026-05-06T00:30:00.000Z",
            observed_at: "2026-05-06T00:31:00.000Z",
            payload_hash: "doc-hash-1",
            normalized_text: "FOMC calendar text",
            raw_payload: { title: "FOMC calendar" },
            trust_level: "official",
            created_at: "2026-05-06T00:30:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/events": {
        items: [
          {
            event_id: "event-1",
            event_type: "macro_calendar",
            title: "FOMC decision",
            summary: "June policy decision.",
            primary_assets: ["FEDFUNDS"],
            event_time: "2026-06-17T18:00:00.000Z",
            status: "scheduled",
            created_at: "2026-05-06T00:30:00.000Z",
            updated_at: "2026-05-06T00:35:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/links": {
        items: [
          {
            link_id: "link-1",
            event_id: "event-1",
            venue: "polymarket",
            venue_market_id: "market-1",
            venue_contract_id: "condition-1",
            outcome_id: "yes-token-1",
            adapter_metadata: { market_slug: "fed-june" },
            outcome: "yes",
            link_reason: "Market resolves from this FOMC decision.",
            link_confidence: 0.93,
            created_at: "2026-05-06T00:36:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/research-runs": {
        items: [
          {
            run_id: "research-1",
            trigger_type: "manual_task",
            opportunity_id: "opp-1",
            evidence_pack_id: "evidence-1",
            strategy_version_id: "strategy-v1",
            event_id: "event-1",
            venue: "polymarket",
            venue_market_id: "market-1",
            requested_by: "analyst",
            status: "completed",
            started_at: "2026-05-06T01:00:00.000Z",
            completed_at: "2026-05-06T01:05:00.000Z",
            model_config: { model: "researcher" },
            created_at: "2026-05-06T01:00:00.000Z"
          }
        ]
      },
      "http://localhost:8765/api/poly-alpha/findings": {
        items: [
          {
            finding_id: "finding-1",
            run_id: "research-1",
            opportunity_id: "opp-1",
            evidence_pack_id: "evidence-1",
            strategy_version_id: "strategy-v1",
            agent_role: "macro-news",
            estimated_probability: 0.64,
            market_probability: 0.58,
            edge: 0.06,
            confidence: 0.72,
            recommendation: "watch",
            thesis: "Policy pricing moved.",
            evidence_ids: ["doc-1"],
            counter_evidence_ids: [],
            resolution_risks: ["ambiguous_resolution"],
            blockers: [],
            created_at: "2026-05-06T01:04:00.000Z"
          }
        ]
      }
    };
    const fetchMock = vi.fn((url: string) => {
      const response = responseByUrl[url];

      if (!response) {
        return Promise.reject(new Error(`unexpected url ${url}`));
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(response)
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchPolyAlphaOpportunities()).resolves.toEqual([
      expect.objectContaining({
        id: "opp-1",
        venueMarketId: "market-1",
        marketProbability: 58,
        estimatedProbability: 64,
        edge: 0.06,
        confidence: 72,
        source: "api"
      })
    ]);
    await expect(fetchPolyAlphaScanRuns()).resolves.toEqual([
      expect.objectContaining({ id: "scan-1", status: "completed", source: "api" })
    ]);
    await expect(fetchPolyAlphaScanResults()).resolves.toEqual([
      expect.objectContaining({
        id: "scan-result-1",
        scanRunId: "scan-1",
        venueMarketId: "market-1",
        sourceSnapshotIds: ["snapshot-1"],
        sourceDocumentIds: ["doc-1"],
        source: "api"
      })
    ]);
    await expect(fetchPolyAlphaMarketSnapshots()).resolves.toEqual([
      expect.objectContaining({
        id: "snapshot-1",
        venueMarketId: "market-1",
        observedAt: "2026-05-06T00:58:00.000Z",
        midPrice: 0.58,
        spread: 0.02,
        bestBid: 0.57,
        bestAsk: 0.59,
        source: "api"
      })
    ]);
    await expect(fetchPolyAlphaDocuments()).resolves.toEqual([
      expect.objectContaining({ id: "doc-1", title: "FOMC calendar", source: "api" })
    ]);
    await expect(fetchPolyAlphaEvents()).resolves.toEqual([
      expect.objectContaining({ id: "event-1", title: "FOMC decision", source: "api" })
    ]);
    await expect(fetchPolyAlphaLinks()).resolves.toEqual([
      expect.objectContaining({ id: "link-1", eventId: "event-1", venueMarketId: "market-1", source: "api" })
    ]);
    await expect(fetchPolyAlphaResearchRuns()).resolves.toEqual([
      expect.objectContaining({ id: "research-1", status: "completed", source: "api" })
    ]);
    await expect(fetchPolyAlphaFindings()).resolves.toEqual([
      expect.objectContaining({ id: "finding-1", runId: "research-1", source: "api" })
    ]);

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/opportunities");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/scan-runs");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/scan-results");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/market-snapshots");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/documents");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/events");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/links");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/research-runs");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8765/api/poly-alpha/findings");
  });

  it("combines poly alpha cockpit resources from their backend api endpoints", async () => {
    const responseByUrl: Record<string, unknown> = {
      "http://localhost:8765/api/poly-alpha/opportunities": {
        items: [{ opportunity_id: "opp-1", venue_market_id: "market-1", title: "Fed path repricing" }]
      },
      "http://localhost:8765/api/poly-alpha/scan-runs": {
        items: [{ scan_run_id: "scan-1", status: "completed" }]
      },
      "http://localhost:8765/api/poly-alpha/shadow-signals": {
        items: [{ shadow_signal_id: "shadow-1", status: "shadow", venue_market_id: "market-1" }]
      },
      "http://localhost:8765/api/poly-alpha/validations": {
        items: [{ validation_id: "validation-1", pass_fail: "pass", shadow_signal_id: "shadow-1" }]
      },
      "http://localhost:8765/api/poly-alpha/promotions": {
        items: [{ promotion_id: "promotion-1", decision: "watch", market_id: "market-1" }]
      }
    };
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(responseByUrl[url])
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const cockpit = await fetchPolyAlphaCockpit();

    expect(cockpit.opportunities).toEqual([
      expect.objectContaining({ id: "opp-1", venueMarketId: "market-1", source: "api" })
    ]);
    expect(cockpit.scanRuns).toEqual([expect.objectContaining({ id: "scan-1", source: "api" })]);
    expect(cockpit.shadowSignals).toEqual([
      expect.objectContaining({ id: "shadow-1", status: "shadow", source: "api" })
    ]);
    expect(cockpit.validations).toEqual([
      expect.objectContaining({ id: "validation-1", passFail: "pass", source: "api" })
    ]);
    expect(cockpit.promotions).toEqual([
      expect.objectContaining({ id: "promotion-1", decision: "watch", source: "api" })
    ]);
  });

  it("keeps poly alpha F3 shadow signal statuses separate from promotion decisions", () => {
    const filters = buildPolyAlphaSignalFilters({
      shadowStatuses: ["shadow", "validated", "rejected", "promoted", "expired", "watch"],
      promotionDecisions: ["watch", "promote", "reject", "defer"]
    });

    expect(filters.shadowStatuses).toEqual(["shadow", "validated", "rejected", "promoted", "expired"]);
    expect(filters.promotionDecisions).toEqual(["watch", "promote", "reject"]);
  });
});
