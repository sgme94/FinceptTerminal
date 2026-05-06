import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TerminalStatus } from "../api/types";
import { mockSkips, mockTerminalSnapshot } from "../data/mockTerminalData";
import { SignalsPage } from "./SignalsPage";

vi.mock("../api/client", () => ({
  getSkips: vi.fn(),
  getTerminalSnapshot: vi.fn()
}));

describe("SignalsPage", () => {
  beforeEach(async () => {
    const client = await import("../api/client");
    vi.mocked(client.getTerminalSnapshot).mockResolvedValue(mockTerminalSnapshot);
    vi.mocked(client.getSkips).mockResolvedValue(mockSkips);
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
});
