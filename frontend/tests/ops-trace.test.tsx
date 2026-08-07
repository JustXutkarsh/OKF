import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import { useOpsTrace } from "@/lib/ops-trace";
import type { UseQueryResult } from "@tanstack/react-query";

function queryLike(state: "pending" | "success" | "error", data?: unknown): UseQueryResult<unknown> {
  return {
    isPending: state === "pending",
    isError: state === "error",
    isSuccess: state === "success",
    data: state === "success" ? data : undefined,
    error: state === "error" ? { code: "NETWORK_ERROR" } : undefined,
  } as unknown as UseQueryResult<unknown>;
}

describe("useOpsTrace", () => {
  it("emits one event per status transition, not re-emits", () => {
    const { result, rerender } = renderHook(
      ({ briefState }: { briefState: "pending" | "success" | "error" }) =>
        useOpsTrace(
          [
            {
              agent: "Briefing Agent",
              query: queryLike(briefState, {
                provider: "groq",
                model: "llama",
                documents_used: ["a", "b"],
              }),
              lifecycle: { phase: briefState === "success" ? "done" : briefState === "error" ? "error" : "working", stageIndex: 0, stages: ["s"] },
            },
          ],
          true
        ),
      { initialProps: { briefState: "pending" as "pending" | "success" | "error" } }
    );
    expect(result.current.filter((e) => e.status === "searching")).toHaveLength(1);

    // Same props → re-render must NOT duplicate the event.
    rerender({ briefState: "pending" });
    expect(result.current.filter((e) => e.status === "searching")).toHaveLength(1);

    // Transition to success adds provenance detail.
    rerender({ briefState: "success" });
    const done = result.current.find((e) => e.status === "completed");
    expect(done).toBeDefined();
    expect(done?.agent).toBe("Briefing Agent");
    expect(done?.detail).toContain("groq/llama");
    expect(done?.detail).toContain("2 docs");
  });

  it("error transitions surface the ApiError code", () => {
    const { result } = renderHook(
      () =>
        useOpsTrace(
          [
            {
              agent: "Critical Analysis Agent",
              query: queryLike("error"),
              lifecycle: { phase: "error", stageIndex: 0, stages: ["s"] },
            },
          ],
          true
        )
    );
    const err = result.current.find((e) => e.status === "error");
    expect(err?.detail).toBe("NETWORK_ERROR");
  });

  it("clears when deactivated (new question / reset)", () => {
    const { result, rerender } = renderHook(
      ({ active }: { active: boolean }) =>
        useOpsTrace(
          [
            {
              agent: "Briefing Agent",
              query: queryLike("success", { provider: "p", model: "m", documents_used: [] }),
              lifecycle: { phase: "done", stageIndex: 0, stages: ["s"] },
            },
          ],
          active
        ),
      { initialProps: { active: true } }
    );
    expect(result.current.length).toBeGreaterThan(0);
    rerender({ active: false });
    expect(result.current).toHaveLength(0);
  });
});
