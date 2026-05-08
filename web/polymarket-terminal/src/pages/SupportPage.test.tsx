import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { supportRoutes } from "../routes/routeConfig";
import { SupportPage } from "./SupportPage";

describe("SupportPage", () => {
  it.each(supportRoutes)("renders explicit disabled behavior for $label", (route) => {
    render(<SupportPage route={route} />);

    expect(screen.getByRole("heading", { name: route.label })).toBeInTheDocument();
    expect(screen.getByText("Disabled in MVP")).toBeInTheDocument();
    expect(screen.getByText(/This support workspace is a placeholder/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `${route.label} disabled` })).toBeDisabled();
  });
});
