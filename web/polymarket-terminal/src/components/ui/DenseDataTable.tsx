import type { ReactNode } from "react";
import { EmptyStatePanel } from "./EmptyStatePanel";

export type DenseDataTableColumn<Row> = {
  key: string;
  header: ReactNode;
  align?: "left" | "right";
  render: (row: Row) => ReactNode;
};

type DenseDataTableProps<Row> = {
  caption: string;
  columns: Array<DenseDataTableColumn<Row>>;
  rows: Row[];
  getRowKey?: (row: Row, index: number) => string;
  emptyTitle?: string;
  emptyDescription?: string;
};

export function DenseDataTable<Row>({
  caption,
  columns,
  rows,
  getRowKey,
  emptyTitle = "No rows",
  emptyDescription
}: DenseDataTableProps<Row>) {
  if (rows.length === 0) {
    return <EmptyStatePanel title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <table className="dense-data-table">
      <caption>{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key} className={column.align === "right" ? "align-right" : undefined}>
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={getRowKey ? getRowKey(row, rowIndex) : rowIndex}>
            {columns.map((column) => (
              <td
                key={column.key}
                className={column.align === "right" ? "align-right" : undefined}
              >
                {column.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
