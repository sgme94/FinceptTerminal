import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProbabilityChart } from "./ProbabilityChart";

vi.mock("lightweight-charts", () => ({
  createChart: vi.fn(() => ({
    addSeries: vi.fn(() => ({ setData: vi.fn() })),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() }))
  })),
  AreaSeries: {},
  ColorType: {
    Solid: "solid"
  }
}));

describe("ProbabilityChart", () => {
  it("renders a non-empty chart container", () => {
    render(
      <ProbabilityChart
        label="Probability history"
        data={[
          { time: "2026-05-01", value: 45 },
          { time: "2026-05-02", value: 53 }
        ]}
      />
    );

    const chart = screen.getByTestId("probability-chart");
    expect(chart).toBeInTheDocument();
    expect(chart).toHaveAttribute("aria-label", "Probability history");
  });
});
