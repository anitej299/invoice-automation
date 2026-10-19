import { it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { api } from "../services/api";
import { useApi } from "./useApi";
it("never exposes a previous endpoint response after navigation", async () => {
  const get = vi
    .spyOn(api, "get")
    .mockResolvedValueOnce({ data: { items: [{ name: "Vendor" }] } })
    .mockImplementationOnce(() => new Promise(() => {}));
  const { result, rerender } = renderHook(({ path }) => useApi(path), {
    initialProps: { path: "/vendors" },
  });
  await waitFor(() =>
    expect(result.current.data).toEqual({ items: [{ name: "Vendor" }] }),
  );
  rerender({ path: "/audit-logs" });
  expect(result.current.data).toBeUndefined();
  get.mockRestore();
});
