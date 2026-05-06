import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuditEvent, TradeProposal } from "../api/types";
import { getAuditEvents, getTradeProposals } from "../api/client";
import { AuditPage } from "./AuditPage";

vi.mock("../api/client", () => ({
  getAuditEvents: vi.fn(),
  getTradeProposals: vi.fn()
}));

const auditEvents: AuditEvent[] = [
  {
    source: "api",
    id: "audit-start",
    deploymentId: "dep-test",
    level: "info",
    message: "Bot start requested",
    actor: "user",
    action: "start",
    result: "accepted",
    createdAt: "2026-05-06T10:00:00.000Z"
  },
  {
    source: "api",
    id: "audit-stop",
    deploymentId: "dep-test",
    level: "warning",
    message: "Bot stop requested",
    actor: "user",
    action: "stop",
    result: "accepted",
    createdAt: "2026-05-06T10:05:00.000Z"
  },
  {
    source: "api",
    id: "audit-approve",
    deploymentId: "dep-test",
    level: "info",
    message: "Proposal approved",
    actor: "user",
    action: "approve",
    result: "approved",
    before: { status: "proposed" },
    after: { status: "approved" },
    createdAt: "2026-05-06T10:10:00.000Z"
  },
  {
    source: "api",
    id: "audit-reject",
    deploymentId: "dep-test",
    level: "info",
    message: "Proposal rejected",
    actor: "user",
    action: "reject",
    result: "rejected",
    before: { status: "proposed" },
    after: { status: "rejected" },
    createdAt: "2026-05-06T10:15:00.000Z"
  }
];

const proposals: TradeProposal[] = [
  {
    source: "api",
    id: "prop-1",
    deploymentId: "dep-test",
    marketId: "mkt-1",
    side: "buy",
    outcome: "yes",
    price: 0.58,
    sizeUsd: 75,
    rationale: "Paper proposal",
    status: "approved",
    createdAt: "2026-05-06T10:08:00.000Z"
  },
  {
    source: "api",
    id: "prop-other",
    deploymentId: "other-dep",
    marketId: "mkt-other",
    side: "buy",
    outcome: "no",
    price: 0.42,
    sizeUsd: 50,
    rationale: "Other deployment proposal",
    status: "proposed",
    createdAt: "2026-05-06T10:09:00.000Z"
  }
];

describe("AuditPage", () => {
  beforeEach(() => {
    vi.mocked(getAuditEvents).mockResolvedValue(auditEvents);
    vi.mocked(getTradeProposals).mockResolvedValue(proposals);
  });

  it("displays filters, control actions, proposal transitions, tabs, and append-only warning", async () => {
    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();
    expect(screen.getByLabelText(/deployment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/action/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/result/i)).toBeInTheDocument();

    const list = screen.getByRole("list", { name: /audit event list/i });
    expect(within(list).getAllByText(/start/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/stop/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/approve/i).length).toBeGreaterThan(0);
    expect(within(list).getAllByText(/reject/i).length).toBeGreaterThan(0);
    expect(within(list).getByText(/proposed -> approved/i)).toBeInTheDocument();
    expect(within(list).getByText(/proposed -> rejected/i)).toBeInTheDocument();

    expect(screen.getByRole("tab", { name: /trades/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /signals/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /proposals/i })).toBeInTheDocument();
    expect(screen.getAllByText(/append-only/i).length).toBeGreaterThan(0);
  });

  it("applies the deployment filter to the proposals tab", async () => {
    const user = userEvent.setup();

    render(<AuditPage />);

    expect(await screen.findByRole("heading", { name: "Audit" })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/deployment/i), "dep-test");
    await user.click(screen.getByRole("tab", { name: /proposals/i }));

    expect(screen.getByText("prop-1")).toBeInTheDocument();
    expect(screen.getByText("mkt-1")).toBeInTheDocument();
    expect(screen.queryByText("prop-other")).not.toBeInTheDocument();
    expect(screen.queryByText("mkt-other")).not.toBeInTheDocument();
  });
});
