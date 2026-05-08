import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TerminalStatus } from "../api/types";
import {
  mockPolyAlphaPromotionDecisions,
  mockPolyAlphaShadowSignals,
  mockPolyAlphaValidationResults,
  mockSkips,
  mockTerminalSnapshot
} from "../data/mockTerminalData";
import { SignalsPage } from "./SignalsPage";

vi.mock("../api/client", () => ({
  buildPolyAlphaSignalFilters: vi.fn((input) => ({
    shadowStatuses: (input.shadowStatuses ?? []).filter((status: string) => status !== "watch"),
    promotionDecisions: input.promotionDecisions ?? []
  })),
  fetchPolyAlphaPromotions: vi.fn(),
  fetchPolyAlphaShadowSignals: vi.fn(),
  fetchPolyAlphaValidations: vi.fn(),
  getSkips: vi.fn(),
  getTerminalSnapshot: vi.fn()
}));

describe("SignalsPage", () => {
  beforeEach(async () => {
    const client = await import("../api/client");
    vi.mocked(client.getTerminalSnapshot).mockResolvedValue(mockTerminalSnapshot);
    vi.mocked(client.getSkips).mockResolvedValue(mockSkips);
    vi.mocked(client.fetchPolyAlphaShadowSignals).mockResolvedValue(mockPolyAlphaShadowSignals);
    vi.mocked(client.fetchPolyAlphaValidations).mockResolvedValue(mockPolyAlphaValidationResults);
    vi.mocked(client.fetchPolyAlphaPromotions).mockResolvedValue(mockPolyAlphaPromotionDecisions);
  });

  it("renders signal edge, confidence, reason, feature contribution, evidence, freshness, and skip rows", async () => {
    render(<SignalsPage />);

    expect(await screen.findByRole("heading", { name: "Signals" })).toBeInTheDocument();

    const signalTable = screen.getByRole("table", { name: "Signal table" });
    expect(within(signalTable).getByText("Rate path repricing")).toBeInTheDocument();
    expect(within(signalTable).getByText("118 bps")).toBeInTheDocument();
    expect(within(signalTable).getByText("64%")).toBeInTheDocument();
    expect(within(signalTable).getByText("Fed implied path moved faster than market price.")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Feature contribution" })).toBeInTheDocument();
    expect(screen.getByText("macro repricing")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Advisory evidence" })).toBeInTheDocument();
    expect(screen.getByText("CME odds update")).toBeInTheDocument();
    expect(screen.getByText("fresh 2m")).toBeInTheDocument();

    const skipTable = screen.getByRole("table", { name: "Skip rows" });
    expect(within(skipTable).getByText("liquidity_below_threshold")).toBeInTheDocument();
    expect(within(skipTable).getByText("mkt-thin-001")).toBeInTheDocument();
  });

  it("does not render nonnumeric feature contributions", async () => {
    const client = await import("../api/client");
    const snapshotWithMixedFeatures: TerminalStatus = {
      ...mockTerminalSnapshot,
      signals: [
        {
          ...mockTerminalSnapshot.signals[0],
          features: { good: 0.42, bad: "x", empty: null } as unknown as Record<string, number>
        }
      ]
    };
    vi.mocked(client.getTerminalSnapshot).mockResolvedValue(snapshotWithMixedFeatures);

    render(<SignalsPage />);

    expect(await screen.findByText("good")).toBeInTheDocument();
    expect(screen.getByText("0.42")).toBeInTheDocument();
    expect(screen.queryByText("bad")).not.toBeInTheDocument();
    expect(screen.queryByText("empty")).not.toBeInTheDocument();
  });

  it("renders Poly Alpha shadow metrics with separate status and promotion decision filters", async () => {
    render(<SignalsPage />);

    expect(await screen.findByRole("heading", { name: "Signals" })).toBeInTheDocument();

    const polyAlphaTable = await screen.findByRole("table", { name: "Poly Alpha shadow signals" });
    expect(within(polyAlphaTable).getAllByText("strategy-v1").length).toBeGreaterThan(0);
    expect(within(polyAlphaTable).getByText("shadow")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("CLV 0.02")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("Brier 0.19")).toBeInTheDocument();
    expect(within(polyAlphaTable).getByText("Calibration 0.04")).toBeInTheDocument();

    const statusFilters = screen.getByLabelText("Shadow status filters");
    expect(within(statusFilters).getByRole("button", { name: "Filter shadow status shadow" })).toBeInTheDocument();
    expect(within(statusFilters).getByRole("button", { name: "Filter shadow status validated" })).toBeInTheDocument();
    expect(within(statusFilters).queryByText("watch")).not.toBeInTheDocument();

    const promotionFilters = screen.getByLabelText("Promotion decision filters");
    expect(within(promotionFilters).getByRole("button", { name: "Filter promotion decision watch" })).toBeInTheDocument();
    expect(within(promotionFilters).getByRole("button", { name: "Filter promotion decision reject" })).toBeInTheDocument();
  });

  it("filters Poly Alpha rows by shadow status", async () => {
    const user = userEvent.setup();

    render(<SignalsPage />);

    const statusFilters = await screen.findByLabelText("Shadow status filters");
    await user.click(within(statusFilters).getByRole("button", { name: "Filter shadow status validated" }));

    const polyAlphaTable = screen.getByRole("table", { name: "Poly Alpha shadow signals" });
    expect(within(polyAlphaTable).getByText("poly-shadow-btc")).toBeInTheDocument();
    expect(within(polyAlphaTable).queryByText("poly-shadow-fed")).not.toBeInTheDocument();
  });

  it("filters Poly Alpha rows by promotion decision independently from shadow status", async () => {
    const user = userEvent.setup();

    render(<SignalsPage />);

    const promotionFilters = await screen.findByLabelText("Promotion decision filters");
    await user.click(within(promotionFilters).getByRole("button", { name: "Filter promotion decision watch" }));

    const statusFilters = screen.getByLabelText("Shadow status filters");
    expect(within(statusFilters).queryByRole("button", { name: /watch/i })).not.toBeInTheDocument();

    const polyAlphaTable = screen.getByRole("table", { name: "Poly Alpha shadow signals" });
    expect(within(polyAlphaTable).getByText("poly-shadow-fed")).toBeInTheDocument();
    expect(within(polyAlphaTable).queryByText("poly-shadow-btc")).not.toBeInTheDocument();
  });
});
