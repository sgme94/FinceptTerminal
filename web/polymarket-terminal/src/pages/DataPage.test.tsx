import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataPage } from "./DataPage";

describe("DataPage", () => {
  it("renders source status, adapter placeholders, cache health, and disabled dataroom", () => {
    render(<DataPage />);

    expect(screen.getByRole("heading", { name: "Data" })).toBeInTheDocument();
    expect(screen.getByText("Polymarket source status")).toBeInTheDocument();
    expect(screen.getByText("OpenBB adapter placeholder")).toBeInTheDocument();
    expect(screen.getByText("public-apis adapter placeholder")).toBeInTheDocument();
    expect(screen.getByText("Sherlock adapter placeholder")).toBeInTheDocument();
    expect(screen.getByText("Cache health")).toBeInTheDocument();
    expect(screen.getByText("Dataroom upload disabled")).toBeInTheDocument();
    expect(screen.getByText(/No credentials, private keys, or API secrets are requested/)).toBeInTheDocument();
  });
});
