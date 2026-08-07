import { describe, expect, it, vi } from "vitest";
import { registerErrorReporter, reportError } from "@/lib/monitoring";
import {
  clearDiagnostics,
  describeDiagnostics,
  getDiagnostics,
  recordDiagnostics,
  diagnosticsContext,
} from "@/lib/diagnostics";

describe("monitoring (Sentry-ready hooks)", () => {
  it("registered reporter receives error + safe context", () => {
    const sink = vi.fn();
    const unregister = registerErrorReporter(sink);

    const err = new Error("boom");
    reportError(err, { route: "/analyze", component: "AnalysisView", requestId: "req-9" });

    expect(sink).toHaveBeenCalledTimes(1);
    expect(sink.mock.calls[0][0]).toBe(err);
    expect(sink.mock.calls[0][1]).toEqual({
      route: "/analyze",
      component: "AnalysisView",
      requestId: "req-9",
    });

    unregister();
    reportError(new Error("after unregister"), {});
    expect(sink).toHaveBeenCalledTimes(1);
  });

  it("a broken reporter never breaks reportError or other reporters", () => {
    const good = vi.fn();
    const bad = vi.fn(() => {
      throw new Error("reporter exploded");
    });
    const unbad = registerErrorReporter(bad);
    const ungood = registerErrorReporter(good);

    expect(() => reportError(new Error("x"), {})).not.toThrow();
    expect(good).toHaveBeenCalled();
    unbad();
    ungood();
  });

  it("falls back to console.error when no reporter is registered", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    reportError(new Error("no reporters"), { component: "test" });
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe("diagnostics registry", () => {
  it("records only safe metadata and stamps duration", () => {
    clearDiagnostics();
    recordDiagnostics("/compare", 42, {
      provider: "openai",
      model: "gpt",
      generated_at: "2026-08-07T00:00:00Z",
      documents_used: ["a", "b", "c"],
      bundle_version: 2,
      request_id: "req-1",
      sources: [{ source_url: "https://example.com", secret: "x" }],
    });

    const snap = getDiagnostics("/compare");
    expect(snap?.documentCount).toBe(3);
    expect(JSON.stringify(snap)).not.toContain("example.com");
    expect(JSON.stringify(snap)).not.toContain("secret");

    expect(describeDiagnostics("/compare")).toContain("request_id req-1");
    expect(diagnosticsContext("/compare").requestId).toBe("req-1");
    expect(getDiagnostics("/never-called")).toBeUndefined();

    clearDiagnostics();
    expect(getDiagnostics("/compare")).toBeUndefined();
  });
});
