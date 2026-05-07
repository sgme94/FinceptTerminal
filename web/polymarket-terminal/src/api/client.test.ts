import { afterEach, describe, expect, it, vi } from "vitest";
import {
  approveTradeProposal,
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
});
