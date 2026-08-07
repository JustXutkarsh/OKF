import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";
import { clearDiagnostics, getDiagnostics } from "@/lib/diagnostics";

// Contract hardening: a malformed payload must never become
// "successful" undefined data — request() must reject loudly and the
// caller (React Query) must land in isError, never a blank render.

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api contract hardening", () => {
  beforeEach(() => {
    clearDiagnostics();
    // Note: fetch is stubbed per-test; loadConfig() safely falls back to
    // DEFAULT_CONFIG in this environment, which is all request() needs.
  });

  it("malformed analyze payload rejects instead of producing undefined data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(200, {
          critical_analysis: { assumptions: ["a"] }, // missing required fields
          reasoning: "x",
        })
      )
    );

    await expect(api.analyze("q")).rejects.toThrow();
    expect(getDiagnostics("/analyze")).toBeUndefined();
    vi.unstubAllGlobals();
  });

  it("valid analyze payload parses and records safe diagnostics", async () => {
    const payload = {
      critical_analysis: {
        assumptions: ["a"],
        conflicting_evidence: [],
        uncertainties: ["u"],
        alternative_interpretations: [],
        missing_information: [],
        confidence_assessment: "confident",
      },
      reasoning: "r",
      documents_used: ["doc-1", "doc-2"],
      evidence: [],
      sources: [],
      retrieval: { candidate_count: 2, selected_count: 2, selected_documents: [], retrieval_time_ms: 1 },
      ranking: [],
      generated_at: "2026-08-07T00:00:00Z",
      provider: "groq",
      model: "llama",
      bundle_version: 1,
      api_key: "SECRET_LEAK_r3fa1b2", // must never be recorded
    };
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, payload)));

    const result = await api.analyze("q");
    expect(result.provider).toBe("groq");

    const snap = getDiagnostics("/analyze");
    expect(snap?.provider).toBe("groq");
    expect(snap?.model).toBe("llama");
    expect(snap?.generatedAt).toBe("2026-08-07T00:00:00Z");
    expect(snap?.documentCount).toBe(2);
    expect(snap?.bundleVersion).toBe(1);
    expect(typeof snap?.durationMs).toBe("number");
    // Never record keys or contents:
    expect(JSON.stringify(snap)).not.toContain("SECRET_LEAK");
    vi.unstubAllGlobals();
  });

  it("backend error envelope surfaces as ApiError with code and request_id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(422, {
          error: { code: "VALIDATION_FAILED", message: "bad question", request_id: "req-123" },
        })
      )
    );

    const err = await api.brief("q").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("VALIDATION_FAILED");
    expect(err.status).toBe(422);
    expect(getDiagnostics("/brief")).toBeUndefined();
    vi.unstubAllGlobals();
  });

  it("non-JSON response yields INVALID_RESPONSE, not undefined", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>proxy error</html>", { status: 502 }))
    );

    const err = await api.analyze("q").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("INVALID_RESPONSE");
    vi.unstubAllGlobals();
  });
});
