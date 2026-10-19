import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Badge, Pagination, Notice } from "./ui";
import { money } from "../services/api";
describe("finance interface", () => {
  it("renders understandable status labels", () => {
    render(<Badge value="UNDER_REVIEW" />);
    expect(screen.getByText("UNDER REVIEW")).toBeInTheDocument();
  });
  it("prevents invalid page navigation", () => {
    const change = vi.fn();
    render(<Pagination page={1} total={21} onChange={change} />);
    expect(screen.getByText("Previous")).toBeDisabled();
    fireEvent.click(screen.getByText("Next"));
    expect(change).toHaveBeenCalledWith(2);
  });
  it("announces API errors", () => {
    render(<Notice error="Connection lost" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Connection lost");
  });
  it("does not turn unknown amounts into zero", () => {
    expect(money(null, "USD")).toBe("—");
    expect(money("123.40", "USD")).toBe("USD 123.40");
  });
});
