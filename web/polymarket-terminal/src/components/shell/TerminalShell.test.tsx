import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TerminalShell } from "./TerminalShell";

describe("TerminalShell", () => {
  it("renders Markets page after clicking F2 Markets", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.click(screen.getByRole("button", { name: "F2 Markets" }));

    expect(screen.getByRole("heading", { name: "Markets" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Market candidates" })).toBeInTheDocument();
  });

  it("renders Risk page after pressing F4", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.keyboard("{F4}");

    expect(screen.getByRole("heading", { name: "Risk" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Proposal approval queue" })).toBeInTheDocument();
  });

  it("keeps the left rail active state in sync with the route", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.click(screen.getByRole("button", { name: "F3 Signals" }));

    expect(screen.getByRole("table", { name: "Signal table" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Signals rail" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("uses the shared route list in the mobile drawer", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await user.click(screen.getByRole("button", { name: "Data drawer" }));

    expect(screen.getByRole("heading", { name: "Data" })).toBeInTheDocument();
  });

  it("renders page-specific content for F5, F6, and F7 routes", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.click(screen.getByRole("button", { name: "F5 News" }));
    expect(screen.getByRole("table", { name: "Mock news feed" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "F6 Data" }));
    expect(screen.getByText("Polymarket source status")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "F7 Agents" }));
    expect(screen.getByText("Agents cannot trade")).toBeInTheDocument();
  });

  it("renders explicit disabled support placeholders from the rail", async () => {
    const user = userEvent.setup();

    render(<TerminalShell />);
    await user.click(screen.getByRole("button", { name: "Strategy Arena rail" }));

    expect(screen.getByRole("heading", { name: "Strategy Arena" })).toBeInTheDocument();
    expect(screen.getByText("Disabled in MVP")).toBeInTheDocument();
  });
});
