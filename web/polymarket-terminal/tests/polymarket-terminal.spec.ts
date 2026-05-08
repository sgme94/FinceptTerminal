import { expect, test, type Page } from "@playwright/test";

const apiBase = "http://127.0.0.1:8765";

const routes = [
  ["F1", "Overview"],
  ["F2", "Markets"],
  ["F3", "Signals"],
  ["F4", "Risk"],
  ["F5", "News"],
  ["F6", "Data"],
  ["F7", "Poly Alpha Cockpit"],
  ["F8", "Audit"]
] as const;

type ManualResearchPayload = {
  opportunity_id: string;
  evidence_pack_id: string;
  strategy_version_id: string;
  venue_market_id: string;
  requested_by: string;
  config?: Record<string, unknown>;
};

type PolyAlphaPaperScenario = "happy" | "blocked";
type PolyAlphaRouteHarness = {
  recordPaperFill: () => void;
  expectNoUnexpectedRequests: () => void;
};

function jsonResponse(body: unknown, status = 200) {
  return {
    status,
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "content-type",
      "content-type": "application/json"
    },
    body: JSON.stringify(body)
  };
}

async function installPolyAlphaPaperOnlyRoutes(page: Page): Promise<PolyAlphaRouteHarness> {
  let scenario: PolyAlphaPaperScenario | null = null;
  let manualResearch: ManualResearchPayload | null = null;
  let proposalStatus = "proposed";
  const paperAuditEvents: Array<Record<string, unknown>> = [];
  const unexpectedRequests: string[] = [];
  const timestamp = "2026-05-08T08:00:00.000Z";

  function baseOpportunity(payload: ManualResearchPayload) {
    return {
      opportunity_id: payload.opportunity_id,
      strategy_version_id: payload.strategy_version_id,
      venue: "polymarket",
      venue_market_id: payload.venue_market_id,
      venue_contract_id: "paper-contract",
      outcome_id: "yes",
      title: `${payload.opportunity_id} manual research task`,
      alpha_family: "event-time-dislocation",
      status: scenario === "blocked" ? "shadow" : "validated",
      primary_reason:
        scenario === "blocked"
          ? "unresolved Critic blocker prevents promotion"
          : "manual research task passed event-time check",
      market_probability: 0.44,
      estimated_probability: scenario === "blocked" ? 0.51 : 0.58,
      edge: scenario === "blocked" ? 0.01 : 0.14,
      confidence: scenario === "blocked" ? 0.4 : 0.72,
      created_at: timestamp,
      updated_at: timestamp
    };
  }

  function fixturesFor(payload: ManualResearchPayload) {
    const isBlocked = scenario === "blocked";
    const runId = isBlocked ? "e2e-run-blocked" : "e2e-run-happy";
    const shadowSignalId = isBlocked ? "e2e-shadow-blocked" : "e2e-shadow-happy";
    const promotionId = isBlocked ? "e2e-promotion-blocked" : "e2e-promotion-happy";

    const polyAlphaAudit = isBlocked
      ? [
          {
            audit_id: "e2e-audit-promotion-rejected",
            action: "promotion_rejected",
            entity_type: "promotion",
            entity_id: "e2e-promotion-blocked",
            opportunity_id: payload.opportunity_id,
            strategy_version_id: payload.strategy_version_id,
            actor_type: "critic",
            actor_id: "paper-fixture",
            before: {},
            after: { decision: "reject" },
            result: "rejected",
            reason: "critic_blocker unresolved_timestamp_conflict",
            request_id: "e2e-request-blocked",
            created_at: timestamp
          }
        ]
      : [
          {
            audit_id: "e2e-audit-exploration",
            action: "exploration_passed",
            entity_type: "exploration",
            entity_id: "e2e-exploration-happy",
            opportunity_id: payload.opportunity_id,
            strategy_version_id: payload.strategy_version_id,
            actor_type: "agent",
            actor_id: "paper-fixture",
            before: {},
            after: { decision: "pass" },
            result: "accepted",
            reason: "exploration_passed",
            request_id: "e2e-request-happy",
            created_at: timestamp
          },
          ...paperAuditEvents
        ];

    return {
      opportunities: [baseOpportunity(payload)],
      researchRuns: [
        {
          run_id: runId,
          trigger_type: "manual",
          opportunity_id: payload.opportunity_id,
          evidence_pack_id: payload.evidence_pack_id,
          strategy_version_id: payload.strategy_version_id,
          event_id: isBlocked ? "e2e-event-blocked" : "e2e-event-happy",
          venue: "polymarket",
          venue_market_id: payload.venue_market_id,
          requested_by: payload.requested_by,
          started_at: timestamp,
          completed_at: timestamp,
          status: isBlocked ? "blocked" : "completed",
          model_config: { paper_fixture: true },
          created_at: timestamp
        }
      ],
      findings: [
        {
          finding_id: isBlocked ? "e2e-finding-blocked" : "e2e-finding-happy",
          run_id: runId,
          opportunity_id: payload.opportunity_id,
          evidence_pack_id: payload.evidence_pack_id,
          strategy_version_id: payload.strategy_version_id,
          agent_role: isBlocked ? "critic" : "researcher",
          estimated_probability: isBlocked ? 0.51 : 0.58,
          market_probability: 0.44,
          edge: isBlocked ? 0.01 : 0.14,
          confidence: isBlocked ? 0.4 : 0.72,
          recommendation: isBlocked ? "reject" : "shadow",
          thesis: isBlocked
            ? "critic_blocker unresolved_timestamp_conflict"
            : "mocked agent findings support a paper-only shadow signal",
          evidence_ids: [isBlocked ? "e2e-doc-blocked" : "e2e-doc-happy"],
          counter_evidence_ids: [],
          resolution_risks: [isBlocked ? "timestamp conflict" : "event-time check passed"],
          blockers: isBlocked ? ["critic_blocker"] : [],
          created_at: timestamp
        }
      ],
      evidencePacks: [
        {
          evidence_pack_id: payload.evidence_pack_id,
          opportunity_id: payload.opportunity_id,
          strategy_version_id: payload.strategy_version_id,
          document_ids: [isBlocked ? "e2e-doc-blocked" : "e2e-doc-happy"],
          snapshot_ids: [isBlocked ? "e2e-entry-blocked" : "e2e-entry-snapshot"],
          event_ids: [isBlocked ? "e2e-event-blocked" : "e2e-event-happy"],
          source_set_version: "paper-fixture-v1",
          latest_published_at: timestamp,
          latest_fetched_at: timestamp,
          latest_observed_at: timestamp,
          created_at: timestamp,
          payload_hash: isBlocked ? "paper-fixture-blocked-hash" : "paper-fixture-hash"
        }
      ],
      explorations: [
        {
          exploration_id: isBlocked ? "e2e-exploration-blocked" : "e2e-exploration-happy",
          opportunity_id: payload.opportunity_id,
          evidence_pack_id: payload.evidence_pack_id,
          strategy_version_id: payload.strategy_version_id,
          decision: isBlocked ? "reject" : "pass",
          reason: isBlocked
            ? "critic_blocker unresolved_timestamp_conflict"
            : "exploration pass after deterministic paper-only research",
          metrics: isBlocked ? { blockers: 1 } : { samples: 24 },
          created_at: timestamp
        }
      ],
      shadowSignals: [
        {
          shadow_signal_id: shadowSignalId,
          opportunity_id: payload.opportunity_id,
          run_id: runId,
          strategy_version_id: payload.strategy_version_id,
          strategy_family: "event-time-dislocation",
          venue: "polymarket",
          venue_market_id: payload.venue_market_id,
          venue_contract_id: isBlocked ? "paper-contract-blocked" : "paper-contract-happy",
          outcome_id: "yes",
          adapter_metadata: { paper_only: true },
          side: "buy",
          observed_price: 0.44,
          estimated_probability: isBlocked ? 0.51 : 0.58,
          edge: isBlocked ? 0.01 : 0.14,
          confidence: isBlocked ? 0.4 : 0.72,
          status: isBlocked ? "rejected" : "validated",
          created_at: timestamp,
          expires_at: "2026-05-09T08:00:00.000Z"
        }
      ],
      validations: [
        {
          validation_id: isBlocked ? "e2e-validation-blocked" : "e2e-validation-happy",
          opportunity_id: payload.opportunity_id,
          shadow_signal_id: shadowSignalId,
          strategy_version_id: payload.strategy_version_id,
          entry_snapshot_id: isBlocked ? "e2e-entry-blocked" : "e2e-entry-snapshot",
          exit_snapshot_id: isBlocked ? "e2e-exit-blocked" : "e2e-exit-snapshot",
          validation_type: "event_time_check",
          entry_price: 0.44,
          exit_price: isBlocked ? 0.44 : 0.47,
          holding_period: "paper",
          gross_return: isBlocked ? 0 : 0.03,
          cost_adjusted_return: isBlocked ? 0 : 0.02,
          closing_line_value: isBlocked ? 0 : 0.03,
          brier_score: isBlocked ? 0.26 : 0.19,
          calibration_error: isBlocked ? 0.12 : 0.02,
          edge_decay: isBlocked ? 0.03 : 0.01,
          information_lag_sec: isBlocked ? 900 : 0,
          fetch_lag_sec: 0,
          market_move_before_signal: isBlocked ? 0.04 : 0,
          market_move_after_signal: isBlocked ? 0 : 0.03,
          max_adverse_excursion: isBlocked ? 0 : 0.01,
          max_favorable_excursion: isBlocked ? 0 : 0.04,
          liquidity_assumption: "paper-only",
          slippage_assumption: "paper-only",
          pass_fail: isBlocked ? "fail" : "pass",
          failure_reason: isBlocked ? "unresolved_timestamp_conflict" : "",
          created_at: timestamp
        }
      ],
      promotions: [
        {
          promotion_id: promotionId,
          opportunity_id: payload.opportunity_id,
          shadow_signal_id: shadowSignalId,
          strategy_version_id: payload.strategy_version_id,
          decision: isBlocked ? "reject" : "promote",
          reason: isBlocked
            ? "critic_blocker unresolved_timestamp_conflict"
            : "event-time check, validation, and mocked agent findings passed",
          prediction_metrics: isBlocked ? {} : { brier_score: 0.19 },
          trading_metrics: isBlocked ? {} : { paper_capacity_usd: 100 },
          metrics: { event_time_check: isBlocked ? "fail" : "pass" },
          critic_blockers: isBlocked ? ["critic_blocker", "unresolved_timestamp_conflict"] : [],
          risk_checks: { paper_only: true },
          proposal_id: isBlocked ? "" : "e2e-proposal-happy",
          decided_at: timestamp
        }
      ],
      proposals: isBlocked
        ? []
        : [
            {
              proposal_id: "e2e-proposal-happy",
              deployment_id: "default",
              strategy_id: payload.strategy_version_id,
              condition_id: "paper-condition-happy",
              asset_id: "paper-asset-happy",
              market_id: payload.venue_market_id,
              side: "buy",
              outcome: "yes",
              price: 0.44,
              size: 25,
              status: proposalStatus,
              reason: "paper-only promoted Poly Alpha proposal",
              created_at: timestamp
            }
          ],
      polyAlphaAudit
    };
  }

  function currentFixtures() {
    if (!manualResearch || !scenario) {
      return null;
    }

    return fixturesFor(manualResearch);
  }

  await page.route(`${apiBase}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;

    if (request.method() === "OPTIONS") {
      await route.fulfill(jsonResponse({}, 204));
      return;
    }

    if (pathname === "/api/poly-alpha/research-runs/manual" && request.method() === "POST") {
      manualResearch = request.postDataJSON() as ManualResearchPayload;
      scenario = manualResearch.config?.critic_blocker ? "blocked" : "happy";
      proposalStatus = "proposed";
      paperAuditEvents.length = 0;
      await route.fulfill(
        jsonResponse({
          run_id: scenario === "blocked" ? "e2e-run-blocked" : "e2e-run-happy",
          status: scenario === "blocked" ? "blocked" : "completed",
          paper_only: true
        })
      );
      return;
    }

    if (pathname === "/api/proposals/e2e-proposal-happy/approve" && request.method() === "POST") {
      proposalStatus = "approved";
      paperAuditEvents.push({
        audit_id: "e2e-audit-proposal-approved",
        action: "proposal_approved",
        entity_type: "proposal",
        entity_id: "e2e-proposal-happy",
        opportunity_id: manualResearch?.opportunity_id ?? "e2e-opp-happy",
        strategy_version_id: manualResearch?.strategy_version_id ?? "strat-v1",
        actor_type: "risk",
        actor_id: "paper-fixture",
        before: { status: "proposed" },
        after: { status: "approved", paper_only: true },
        result: "accepted",
        reason: "manual approval accepted for paper workflow",
        request_id: "e2e-request-approve",
        created_at: timestamp
      });
      await route.fulfill(
        jsonResponse(
          {
            accepted: true,
            action: "approve",
            status: "approved",
            paper_only: true
          },
          202
        )
      );
      return;
    }

    const fixtures = currentFixtures();

    if (pathname === "/api/bot/status") {
      await route.fulfill(
        jsonResponse({
          mode: "paper",
          live_enabled: false,
          approval_mode: "manual",
          status: "running",
          healthy: true
        })
      );
      return;
    }

    if (pathname === "/api/audit") {
      const events =
        fixtures?.polyAlphaAudit.map((event) => ({
          event_id: `general-${String(event.audit_id)}`,
          deployment_id: "default",
          strategy_id: "strat-v1",
          actor_type: event.actor_type,
          actor_id: event.actor_id,
          action: event.action,
          entity_type: event.entity_type,
          entity_id: event.entity_id,
          before: event.before,
          after: event.after,
          result: event.result,
          reason: event.reason,
          request_id: event.request_id,
          created_at: event.created_at
        })) ?? [];
      await route.fulfill(jsonResponse({ events }));
      return;
    }

    if (pathname === "/api/proposals") {
      await route.fulfill(jsonResponse({ proposals: fixtures?.proposals ?? [] }));
      return;
    }

    const emptyLists: Record<string, unknown> = {
      "/api/trades": { trades: [] },
      "/api/positions": { positions: [] },
      "/api/candidates": { candidates: [] },
      "/api/signals": { signals: [] },
      "/api/skips": { skips: [] }
    };

    if (pathname in emptyLists) {
      await route.fulfill(jsonResponse(emptyLists[pathname]));
      return;
    }

    const polyAlphaLists: Record<string, unknown[]> = {
      "/api/poly-alpha/opportunities": fixtures?.opportunities ?? [],
      "/api/poly-alpha/scan-runs": [],
      "/api/poly-alpha/scan-results": [],
      "/api/poly-alpha/market-snapshots": [],
      "/api/poly-alpha/documents": [],
      "/api/poly-alpha/events": [],
      "/api/poly-alpha/links": [],
      "/api/poly-alpha/research-runs": fixtures?.researchRuns ?? [],
      "/api/poly-alpha/findings": fixtures?.findings ?? [],
      "/api/poly-alpha/evidence-packs": fixtures?.evidencePacks ?? [],
      "/api/poly-alpha/exploration-decisions": fixtures?.explorations ?? [],
      "/api/poly-alpha/audit": fixtures?.polyAlphaAudit ?? [],
      "/api/poly-alpha/shadow-signals": fixtures?.shadowSignals ?? [],
      "/api/poly-alpha/validations": fixtures?.validations ?? [],
      "/api/poly-alpha/promotions": fixtures?.promotions ?? []
    };

    if (pathname in polyAlphaLists) {
      await route.fulfill(jsonResponse({ items: polyAlphaLists[pathname] }));
      return;
    }

    unexpectedRequests.push(`${request.method()} ${pathname}`);
    await route.fulfill(
      jsonResponse(
        {
          error: "Unhandled fixture route",
          method: request.method(),
          pathname
        },
        500
      )
    );
  });

  return {
    recordPaperFill() {
      proposalStatus = "filled";
      paperAuditEvents.push({
        audit_id: "e2e-audit-paper-fill",
        action: "paper_fill_recorded",
        entity_type: "proposal",
        entity_id: "e2e-proposal-happy",
        opportunity_id: manualResearch?.opportunity_id ?? "e2e-opp-happy",
        strategy_version_id: manualResearch?.strategy_version_id ?? "strat-v1",
        actor_type: "runner",
        actor_id: "paper-fixture",
        before: { status: "approved" },
        after: { status: "filled", paper_only: true },
        result: "accepted",
        reason: "runner recorded a paper fill after manual approval",
        request_id: "e2e-request-fill",
        created_at: timestamp
      });
    },
    expectNoUnexpectedRequests() {
      expect(unexpectedRequests).toEqual([]);
    }
  };
}

test.describe("Polymarket terminal visual shell", () => {
  test("desktop 1700x900 loads shell with right rail and no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 1700, height: 900 });
    const statusResponse = page.waitForResponse("http://127.0.0.1:8765/api/bot/status");
    const positionsResponse = page.waitForResponse("http://127.0.0.1:8765/api/positions?deployment_id=default");
    const tradesResponse = page.waitForResponse("http://127.0.0.1:8765/api/trades?deployment_id=default");
    await page.goto("/");
    expect((await statusResponse).ok()).toBe(true);
    expect((await positionsResponse).ok()).toBe(true);
    expect((await tradesResponse).ok()).toBe(true);

    await expect(page.getByLabel("Polymarket terminal")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("mock fallback")).toBeHidden();
    const contextRail = page.getByLabel("Context rail");
    await expect(contextRail).toBeVisible();
    await expect(contextRail.getByRole("heading", { name: "Live News", exact: true })).toBeVisible();

    const hasOverflow = await page.evaluate(() => {
      const root = document.documentElement;
      return root.scrollWidth > root.clientWidth || document.body.scrollWidth > window.innerWidth;
    });
    expect(hasOverflow).toBe(false);
  });

  test("mobile 390x844 loads drawer, collapses right rail, and has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
    await page.getByRole("button", { name: "Open menu" }).click();
    await expect(page.getByLabel("Mobile route drawer")).toBeVisible();
    await expect(page.getByRole("button", { name: "Risk drawer" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Audit drawer" })).toBeVisible();
    await expect(page.getByLabel("Context rail")).toBeHidden();

    const hasOverflow = await page.evaluate(() => {
      const root = document.documentElement;
      return root.scrollWidth > root.clientWidth || document.body.scrollWidth > window.innerWidth;
    });
    expect(hasOverflow).toBe(false);
  });

  test("F1-F8 keyboard shortcuts switch full route page titles", async ({ page }) => {
    await page.setViewportSize({ width: 1700, height: 900 });
    await page.goto("/");

    for (const [key, title] of routes) {
      await page.keyboard.press(key);
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    }
  });
});

test.describe("Poly Alpha paper-only lifecycle", () => {
  test("happy path promotes a manual research task into a paper fill with F8 evidence chain", async ({ page }) => {
    const routeHarness = await installPolyAlphaPaperOnlyRoutes(page);
    await page.goto("/");
    const manualResearch = await page.evaluate(async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/poly-alpha/research-runs/manual`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          opportunity_id: "e2e-opp-happy",
          evidence_pack_id: "e2e-pack-happy",
          strategy_version_id: "strat-v1",
          venue_market_id: "e2e-market-happy",
          requested_by: "e2e-user",
          config: { model: "mocked-agent-findings" }
        })
      });

      return { ok: response.ok, body: await response.json() };
    }, apiBase);
    expect(manualResearch).toMatchObject({
      ok: true,
      body: { run_id: "e2e-run-happy", status: "completed", paper_only: true }
    });

    await page.keyboard.press("F7");
    await expect(page.getByRole("heading", { name: "Poly Alpha Cockpit" })).toBeVisible();
    await expect(page.getByRole("table", { name: "Today's opportunities" })).toContainText("e2e-opp-happy");
    await expect(page.getByRole("table", { name: "Shadow performance" })).toContainText("e2e-shadow-happy");
    await expect(page.getByRole("table", { name: "Ready for promotion" })).toContainText("mocked agent findings");
    await expect(page.getByRole("table", { name: "Ready for promotion" })).toContainText("event-time check");
    await expect(page.getByRole("table", { name: "Risk queue candidates" })).toContainText("e2e-proposal-happy");

    await page.keyboard.press("F4");
    await expect(page.getByRole("heading", { name: "Risk", exact: true })).toBeVisible();
    await expect(page.getByRole("table", { name: "Poly Alpha Risk queue" })).toContainText("e2e-proposal-happy");
    page.on("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Approve e2e-proposal-happy" }).click();
    await expect(page.getByRole("table", { name: "Proposal approval queue" })).toContainText("approved");
    routeHarness.recordPaperFill();

    await page.keyboard.press("F8");
    await expect(page.getByRole("heading", { name: "Audit", exact: true })).toBeVisible();
    const evidenceChain = page.getByRole("table", { name: "Poly Alpha evidence chain" });
    await expect(evidenceChain).toContainText("e2e-pack-happy");
    await expect(evidenceChain).toContainText("exploration_passed");
    await expect(evidenceChain).toContainText("pass");
    await expect(evidenceChain).toContainText("paper_fill_recorded");
    routeHarness.expectNoUnexpectedRequests();
  });

  test("critic blocker rejects promotion without a Risk queue proposal and audits the rejection", async ({ page }) => {
    const routeHarness = await installPolyAlphaPaperOnlyRoutes(page);
    await page.goto("/");
    const manualResearch = await page.evaluate(async (baseUrl) => {
      const response = await fetch(`${baseUrl}/api/poly-alpha/research-runs/manual`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          opportunity_id: "e2e-opp-blocked",
          evidence_pack_id: "e2e-pack-blocked",
          strategy_version_id: "strat-v1",
          venue_market_id: "e2e-market-blocked",
          requested_by: "e2e-user",
          config: { critic_blocker: "unresolved_timestamp_conflict" }
        })
      });

      return { ok: response.ok, body: await response.json() };
    }, apiBase);
    expect(manualResearch).toMatchObject({
      ok: true,
      body: { run_id: "e2e-run-blocked", status: "blocked", paper_only: true }
    });

    await page.keyboard.press("F7");
    await expect(page.getByRole("heading", { name: "Poly Alpha Cockpit" })).toBeVisible();
    await expect(page.getByRole("table", { name: "Today's opportunities" })).toContainText("e2e-opp-blocked");
    await expect(page.getByRole("table", { name: "Failed and why" })).toContainText("critic_blocker");
    await expect(page.getByRole("table", { name: "Failed and why" })).toContainText(
      "unresolved_timestamp_conflict"
    );

    await page.keyboard.press("F4");
    await expect(page.getByRole("heading", { name: "Risk", exact: true })).toBeVisible();
    await expect(page.getByText("No Poly Alpha promoted proposals")).toBeVisible();
    await expect(page.getByText("e2e-proposal-blocked")).toHaveCount(0);

    await page.keyboard.press("F8");
    await expect(page.getByRole("heading", { name: "Audit", exact: true })).toBeVisible();
    await expect(page.getByLabel("Audit event list")).toContainText("promotion_rejected");
    await expect(page.getByLabel("Audit event list")).toContainText("critic_blocker");
    routeHarness.expectNoUnexpectedRequests();
  });
});
