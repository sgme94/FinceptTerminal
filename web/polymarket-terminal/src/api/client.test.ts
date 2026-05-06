import { afterEach, describe, expect, it, vi } from "vitest";
import { getAuditEvents, getBotStatus, getTerminalSnapshot, getTradeProposals } from "./client";

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

  it("returns mock bot status when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const status = await getBotStatus();

    expect(status.source).toBe("mock");
    expect(status.stale).toBe(true);
    expect(status.mode).toBe("advisory");
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
    expect(snapshot.markets.length).toBeGreaterThan(0);
    expect(snapshot.signals.length).toBeGreaterThan(0);
    expect(snapshot.riskLimits.length).toBeGreaterThan(0);
  });
});
