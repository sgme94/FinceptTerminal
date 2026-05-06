import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TradeProposal } from "../api/types";
import { mockAuditEvents, mockRiskLimits, mockSkips, mockTradeProposals } from "../data/mockTerminalData";
import { RiskPage } from "./RiskPage";

vi.mock("../api/client", () => ({
  approveTradeProposal: vi.fn(),
  getAuditEvents: vi.fn(),
  getRiskLimits: vi.fn(),
  getSkips: vi.fn(),
  getTradeProposals: vi.fn(),
  rejectTradeProposal: vi.fn(),
  triggerKillSwitch: vi.fn()
}));

describe("RiskPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const client = await import("../api/client");
    vi.mocked(client.getTradeProposals).mockResolvedValue(mockTradeProposals);
    vi.mocked(client.getRiskLimits).mockResolvedValue(mockRiskLimits);
    vi.mocked(client.getAuditEvents).mockResolvedValue(mockAuditEvents);
    vi.mocked(client.getSkips).mockResolvedValue(mockSkips);
    vi.mocked(client.approveTradeProposal).mockResolvedValue(undefined);
    vi.mocked(client.rejectTradeProposal).mockResolvedValue(undefined);
    vi.mocked(client.triggerKillSwitch).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders risk limits and every proposal lifecycle status", async () => {
    render(<RiskPage />);

    expect(await screen.findByRole("heading", { name: "Risk" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk limits" })).toBeInTheDocument();
    expect(screen.getByText("Total exposure")).toBeInTheDocument();

    const queue = screen.getByRole("table", { name: "Proposal approval queue" });
    for (const status of ["proposed", "approved", "rejected", "expired", "cancelled", "filled", "failed"]) {
      expect(within(queue).getByText(status)).toBeInTheDocument();
    }
  });

  it("requires confirmation before approve, reject, and kill switch API calls with loaded deployment", async () => {
    const user = userEvent.setup();
    const confirmMock = vi.spyOn(window, "confirm");
    confirmMock.mockReturnValueOnce(false).mockReturnValueOnce(true).mockReturnValueOnce(true).mockReturnValueOnce(true);

    const client = await import("../api/client");
    const proposed: TradeProposal = {
      ...mockTradeProposals[0],
      id: "prop-dep-1",
      deploymentId: "dep-1",
      status: "proposed"
    };
    vi.mocked(client.getTradeProposals).mockResolvedValue([proposed]);

    render(<RiskPage />);

    await screen.findByRole("heading", { name: "Risk" });
    await user.click(screen.getByRole("button", { name: "Approve prop-dep-1" }));
    expect(client.approveTradeProposal).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Approve prop-dep-1" }));
    expect(client.approveTradeProposal).toHaveBeenCalledWith(
      "prop-dep-1",
      expect.objectContaining({
        deployment_id: "dep-1",
        strategy_id: "manual",
        actor_id: "local-user"
      })
    );

    await user.click(screen.getByRole("button", { name: "Reject prop-dep-1" }));
    expect(client.rejectTradeProposal).toHaveBeenCalledWith(
      "prop-dep-1",
      expect.objectContaining({
        deployment_id: "dep-1",
        reason: "Rejected from paper risk page"
      })
    );

    await user.click(screen.getByRole("button", { name: "Paper kill switch" }));
    expect(client.triggerKillSwitch).toHaveBeenCalledWith(
      expect.objectContaining({
        deployment_id: "dep-1",
        reason: "Paper kill switch requested from risk page"
      })
    );
  });

  it("refreshes proposals and audit events after a successful approve", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = await import("../api/client");
    vi.mocked(client.getTradeProposals).mockResolvedValue([
      {
        ...mockTradeProposals[0],
        id: "prop-refresh",
        deploymentId: "dep-refresh",
        status: "proposed"
      }
    ]);

    render(<RiskPage />);

    await screen.findByRole("button", { name: "Approve prop-refresh" });
    await user.click(screen.getByRole("button", { name: "Approve prop-refresh" }));

    await waitFor(() => {
      expect(client.getTradeProposals).toHaveBeenCalledTimes(2);
      expect(client.getAuditEvents).toHaveBeenCalledTimes(2);
    });
  });

  it("shows a visible error when approval fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = await import("../api/client");
    vi.mocked(client.getTradeProposals).mockResolvedValue([
      {
        ...mockTradeProposals[0],
        id: "prop-error",
        deploymentId: "dep-error",
        status: "proposed"
      }
    ]);
    vi.mocked(client.approveTradeProposal).mockRejectedValue(new Error("Request failed: 409"));

    render(<RiskPage />);

    await screen.findByRole("button", { name: "Approve prop-error" });
    await user.click(screen.getByRole("button", { name: "Approve prop-error" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed: 409");
  });
});
