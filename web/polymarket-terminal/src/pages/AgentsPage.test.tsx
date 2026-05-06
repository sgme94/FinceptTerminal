import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentsPage } from "./AgentsPage";

describe("AgentsPage", () => {
  it("renders advisory agent sentinels, research cycles, findings, and disabled agent placeholders", () => {
    render(<AgentsPage />);

    expect(screen.getByRole("heading", { name: "Agents" })).toBeInTheDocument();
    expect(screen.getByText("Agents cannot trade")).toBeInTheDocument();
    expect(screen.getByText("Unverified generated claims are marked unverified.")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Event sentinels" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Research cycles" })).toBeInTheDocument();

    const findingsTable = screen.getByRole("table", { name: "Findings and dissent" });
    expect(within(findingsTable).getByText("Dissent")).toBeInTheDocument();
    expect(within(findingsTable).getByText("Confidence")).toBeInTheDocument();
    expect(within(findingsTable).getByText("unverified")).toBeInTheDocument();

    expect(screen.getByText("TradingAgents placeholder")).toBeInTheDocument();
    expect(screen.getByText("dexter placeholder")).toBeInTheDocument();
    expect(screen.getByText("MiroFish placeholder")).toBeInTheDocument();
  });
});
