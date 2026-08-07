import { describe, expect, it } from "vitest";
import { deriveStatus } from "@/lib/agent-lifecycle";
import { confidenceProfile } from "@/components/confidence-viz";

describe("status derivation", () => {
  it("maps lifecycle phases+stages to user-facing statuses", () => {
    expect(deriveStatus({ phase: "idle", stageIndex: 0 })).toBe("idle");
    expect(deriveStatus({ phase: "done", stageIndex: 0 })).toBe("completed");
    expect(deriveStatus({ phase: "error", stageIndex: 3 })).toBe("error");

    // Working: retrieval → analyzing → writing, deterministic by stage.
    expect(deriveStatus({ phase: "working", stageIndex: 0 })).toBe("searching");
    expect(deriveStatus({ phase: "working", stageIndex: 1 })).toBe("analyzing");
    expect(deriveStatus({ phase: "working", stageIndex: 2 })).toBe("analyzing");
    expect(deriveStatus({ phase: "working", stageIndex: 3 })).toBe("writing");
    expect(deriveStatus({ phase: "working", stageIndex: 4 })).toBe("writing");
  });
});

describe("confidenceProfile", () => {
  it("tallies verified/mixed/unverified, case-insensitive; ignores others", () => {
    const evidence = [
      { confidence: "verified" },
      { confidence: "verified" },
      { confidence: "Mixed" },
      { confidence: "unverified" },
      { confidence: "unknown-label" },
      { confidence: "" },
    ] as never[];
    expect(confidenceProfile(evidence)).toEqual({ verified: 2, mixed: 1, unverified: 1 });
  });

  it("returns zeros when there is no evidence", () => {
    expect(confidenceProfile([])).toEqual({ verified: 0, mixed: 0, unverified: 0 });
  });
});
