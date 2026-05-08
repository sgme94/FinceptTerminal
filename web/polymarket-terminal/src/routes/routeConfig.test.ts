import { describe, expect, it } from "vitest";
import { primaryRoutes, supportRoutes } from "./routeConfig";

describe("routeConfig", () => {
  it("defines exactly eight primary routes", () => {
    expect(primaryRoutes).toHaveLength(8);
  });

  it("maps F1-F8 to the primary workspace routes", () => {
    expect(primaryRoutes.map((route) => [route.functionKey, route.id, route.label])).toEqual([
      ["F1", "overview", "Overview"],
      ["F2", "markets", "Markets"],
      ["F3", "signals", "Signals"],
      ["F4", "risk", "Risk"],
      ["F5", "news", "News"],
      ["F6", "data", "Data"],
      ["F7", "agents", "Agents"],
      ["F8", "audit", "Audit"]
    ]);
  });

  it("defines support routes without function key shortcuts", () => {
    expect(supportRoutes.map((route) => route.id)).toEqual([
      "strategy-arena",
      "watchlist",
      "dataroom",
      "plans-credits",
      "settings",
      "logout"
    ]);

    expect(supportRoutes.every((route) => !("functionKey" in route))).toBe(true);
  });
});
