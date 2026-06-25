import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PricingTable } from "./PricingTable";

describe("PricingTable", () => {
  it("marks every public plan as coming soon instead of showing active prices", () => {
    render(<PricingTable />);

    expect(screen.getAllByText("Coming soon")).toHaveLength(4);
    expect(screen.queryByText("$")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /join early access/i })).toHaveLength(4);
    expect(screen.getByText(/plan packaging is not active yet/i)).toBeInTheDocument();
  });
});
