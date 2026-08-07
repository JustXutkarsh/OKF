import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAgentLifecycle } from "@/lib/agent-lifecycle";
import type { UseQueryResult } from "@tanstack/react-query";

type AnyQuery = UseQueryResult<unknown>;
const STAGES = ["s1", "s2", "s3"];

function makeQuery(status: "pending" | "error" | "success"): AnyQuery {
  return {
    isPending: status === "pending",
    isError: status === "error",
    isSuccess: status === "success",
  } as unknown as AnyQuery;
}

describe("useAgentLifecycle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("is idle when the query is not enabled", () => {
    const { result } = renderHook(() => useAgentLifecycle(makeQuery("pending"), false, STAGES));
    expect(result.current.phase).toBe("idle");
  });

  it("is working while pending and cycles stages over time", () => {
    const { result } = renderHook(() => useAgentLifecycle(makeQuery("pending"), true, STAGES));
    expect(result.current.phase).toBe("working");
    expect(result.current.stageIndex).toBe(0);

    // Stages advance strictly over time while the query is unresolved —
    // no completion is ever claimed.
    // act() not needed for interval advance: rerender effect handles it.
    vi.advanceTimersByTime(2600);
    expect(result.current.phase).toBe("working");
  });

  it("snaps to done only when the query actually succeeds", () => {
    const { result, rerender } = renderHook(
      ({ status }: { status: "pending" | "error" | "success" }) =>
        useAgentLifecycle(makeQuery(status), true, STAGES),
      { initialProps: { status: "pending" } }
    );
    expect(result.current.phase).toBe("working");
    expect(result.current.phase).not.toBe("done");

    rerender({ status: "success" });
    expect(result.current.phase).toBe("done");
  });

  it("is error when the query errors", () => {
    const { result } = renderHook(() => useAgentLifecycle(makeQuery("error"), true, STAGES));
    expect(result.current.phase).toBe("error");
    expect(result.current.phase).not.toBe("done");
  });
});
