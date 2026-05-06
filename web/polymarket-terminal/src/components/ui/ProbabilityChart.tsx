import { useEffect, useRef } from "react";
import { AreaSeries, ColorType, createChart, type Time } from "lightweight-charts";
import type { ProbabilityPoint } from "../../api/types";

type ProbabilityChartProps = {
  label: string;
  data: ProbabilityPoint[];
};

export function ProbabilityChart({ label, data }: ProbabilityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;

    if (!container) {
      return undefined;
    }

    const chart = createChart(container, {
      height: 180,
      layout: {
        background: { type: ColorType.Solid, color: "#0b0b0a" },
        textColor: "#9a8f83"
      },
      grid: {
        horzLines: { color: "#1f1a15" },
        vertLines: { color: "#1f1a15" }
      },
      rightPriceScale: {
        borderColor: "#2a2118"
      },
      timeScale: {
        borderColor: "#2a2118"
      }
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#ff9d2e",
      topColor: "rgba(255, 157, 46, 0.32)",
      bottomColor: "rgba(255, 157, 46, 0.02)"
    });

    series.setData(data.map((point) => ({ time: point.time as Time, value: point.value })));
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [data]);

  return (
    <div
      ref={containerRef}
      className="probability-chart"
      data-testid="probability-chart"
      aria-label={label}
    />
  );
}
