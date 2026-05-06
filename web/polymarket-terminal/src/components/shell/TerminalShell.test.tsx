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
});
