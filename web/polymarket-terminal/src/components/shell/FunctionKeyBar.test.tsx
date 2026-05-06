import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { primaryRoutes } from "../../routes/routeConfig";
import { FunctionKeyBar } from "./FunctionKeyBar";

describe("FunctionKeyBar", () => {
  it("selects a workspace route from the F-key bar", async () => {
    const user = userEvent.setup();
    const onSelectRoute = vi.fn();

    render(
      <FunctionKeyBar
        activeRouteId="overview"
        routes={primaryRoutes}
        onSelectRoute={onSelectRoute}
      />
    );

    await user.click(screen.getByRole("button", { name: "F2 Markets" }));

    expect(onSelectRoute).toHaveBeenCalledWith("markets");
  });

  it("marks the active F-key route", () => {
    render(
      <FunctionKeyBar activeRouteId="risk" routes={primaryRoutes} onSelectRoute={() => {}} />
    );

    expect(screen.getByRole("button", { name: "F4 Risk" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });
});
