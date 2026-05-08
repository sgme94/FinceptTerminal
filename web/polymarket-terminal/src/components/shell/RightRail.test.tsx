import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RightRail, type RightRailSection } from "./RightRail";

describe("RightRail", () => {
  it("renders live news, watchlist, most active, and risk alerts", () => {
    render(<RightRail />);

    expect(screen.getByRole("heading", { name: "Live News" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Watchlist" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Most Active" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk Alerts" })).toBeInTheDocument();
  });

  it("renders section empty and error states without throwing", () => {
    const sections: RightRailSection[] = [
      { id: "live-news", title: "Live News", items: [], emptyLabel: "No live news" },
      { id: "watchlist", title: "Watchlist", error: "Watchlist source unavailable" },
      { id: "most-active", title: "Most Active", items: [], emptyLabel: "No active markets" },
      { id: "risk-alerts", title: "Risk Alerts", error: "Risk source unavailable" }
    ];

    render(<RightRail sections={sections} />);

    expect(screen.getByText("No live news")).toBeInTheDocument();
    const watchlist = screen.getByRole("region", { name: "Watchlist" });
    expect(within(watchlist).getByText("Watchlist source unavailable")).toBeInTheDocument();
    expect(screen.getByText("Risk source unavailable")).toBeInTheDocument();
  });
});
