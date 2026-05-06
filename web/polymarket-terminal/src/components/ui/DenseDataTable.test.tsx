import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DenseDataTable, type DenseDataTableColumn } from "./DenseDataTable";

type Row = {
  market: string;
  probability: string;
};

const columns: DenseDataTableColumn<Row>[] = [
  { key: "market", header: "Market", render: (row) => row.market },
  { key: "probability", header: "Probability", render: (row) => row.probability }
];

describe("DenseDataTable", () => {
  it("renders a stable empty state when rows are empty", () => {
    render(
      <DenseDataTable
        caption="Candidate markets"
        columns={columns}
        rows={[]}
        emptyTitle="No markets"
        emptyDescription="No candidate markets available."
      />
    );

    expect(screen.getByText("No markets")).toBeInTheDocument();
    expect(screen.getByText("No candidate markets available.")).toBeInTheDocument();
  });
});
