import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockPolyAlphaEvidencePacks, mockPolyAlphaScanRuns } from "../data/mockTerminalData";
import { NewsPage } from "./NewsPage";

vi.mock("../api/client", () => ({
  fetchPolyAlphaEvidencePacks: vi.fn(),
  fetchPolyAlphaScanRuns: vi.fn()
}));

describe("NewsPage", () => {
  beforeEach(async () => {
    const client = await import("../api/client");
    vi.mocked(client.fetchPolyAlphaEvidencePacks).mockResolvedValue(mockPolyAlphaEvidencePacks);
    vi.mocked(client.fetchPolyAlphaScanRuns).mockResolvedValue(mockPolyAlphaScanRuns);
  });

  it("renders a dense advisory news list with impact tags and freshness", async () => {
    render(<NewsPage />);

    expect(await screen.findByRole("heading", { name: "News" })).toBeInTheDocument();
    expect(screen.getByText("Advisory read-only feed")).toBeInTheDocument();

    const table = screen.getByRole("table", { name: "Mock news feed" });
    expect(within(table).getByText("High impact")).toBeInTheDocument();
    expect(within(table).getByText("Polymarket blog")).toBeInTheDocument();
    expect(within(table).getByText("fresh 4m")).toBeInTheDocument();
  });

  it("shows Poly Alpha evidence packs and scan runs in the read-only feed", async () => {
    render(<NewsPage />);

    expect(await screen.findByRole("heading", { name: "News" })).toBeInTheDocument();

    const evidenceTable = await screen.findByRole("table", { name: "Evidence packs" });
    expect(within(evidenceTable).getByText("poly-evidence-fed")).toBeInTheDocument();
    expect(within(evidenceTable).getByText("2026-05-06T10:28:00.000Z")).toBeInTheDocument();

    const scanTable = screen.getByRole("table", { name: "Scan runs" });
    expect(within(scanTable).getByText("poly-scan-001")).toBeInTheDocument();
    expect(within(scanTable).getByText("completed")).toBeInTheDocument();
  });
});
