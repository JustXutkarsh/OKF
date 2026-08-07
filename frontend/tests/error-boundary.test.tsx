import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/error-boundary";
import { AnalysisContent } from "@/components/analysis-view";
import { AgentOpsCenter } from "@/components/agent-workspace";
import { recordDiagnostics, clearDiagnostics } from "@/lib/diagnostics";
import type { Analysis } from "@/lib/types";

function Bomb({ message }: { message: string }): never {
  throw new Error(message);
}

// Silence React's expected error logging for thrown-component tests.
function silenceConsoleError(): () => void {
  const spy = vi.spyOn(console, "error").mockImplementation(() => {});
  return () => spy.mockRestore();
}

describe("ErrorBoundary regression", () => {
  afterEach(() => {
    clearDiagnostics();
  });

  it("renders an error card (never blank) when a child throws", () => {
    const restore = silenceConsoleError();
    recordDiagnostics("/analyze", 123, {
      provider: "groq",
      model: "llama",
      generated_at: "2026-08-07T00:00:00Z",
      request_id: "req-abc",
    });

    render(
      <ErrorBoundary scope="Critical analysis" route="/analyze">
        <Bomb message="TypeError: cannot read property 'map' of undefined" />
      </ErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/failed to render/i)).toBeInTheDocument();
    expect(screen.getByRole("alert").textContent).toContain("route /analyze");
    expect(screen.getByRole("alert").textContent).toContain("request_id req-abc");
    restore();
  });

  it("healthy sibling survives when a sibling panel crashes (compare isolation)", () => {
    const restore = silenceConsoleError();

    render(
      <div data-testid="row">
        <ErrorBoundary scope="Briefing (compare tab)" route="/brief">
          <Bomb message="crash in briefing panel" />
        </ErrorBoundary>
        <ErrorBoundary scope="Critical analysis (compare tab)" route="/analyze">
          <p>Analysis content rendered fine</p>
        </ErrorBoundary>
      </div>
    );

    // One boundary shows its error card...
    expect(screen.getByRole("alert").textContent).toContain("Briefing (compare tab) failed");
    // ...and the other panel is untouched — the compare view survives.
    expect(screen.getByText("Analysis content rendered fine")).toBeInTheDocument();
    restore();
  });

  it("renders children normally when nothing throws", () => {
    render(
      <ErrorBoundary scope="Critical analysis" route="/analyze">
        <p>all good</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("Analysis page can never render blank", () => {
  afterEach(() => {
    clearDiagnostics();
    vi.restoreAllMocks();
  });

  it("malformed backend payload lands on the error card, not a blank page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        new Response(
          JSON.stringify(String(input).includes("/brief")
            ? { answer: { current_situation: "x", key_developments: [], key_actors: [] },
                reasoning: "", documents_used: [], evidence: [], sources: [],
                retrieval: { candidate_count: 0, selected_count: 0, selected_documents: [], retrieval_time_ms: 0 },
                ranking: [], generated_at: "", provider: "p", model: "m" }
            : { critical_analysis: { assumptions: ["a"] } }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
    );

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <AgentOpsCenter params={{ question: "q", maxDocs: 1 }} />
      </QueryClientProvider>
    );

    // The malformed analyze payload must land on a visible error surface —
    // never an empty workspace.
    const card = await screen.findByText("ERROR", undefined, { timeout: 10000 });
    expect(card).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("AnalysisContent wrapped in boundary shows error card instead of crashing the tree", () => {
    const restore = silenceConsoleError();
    const poisoned = {
      // critically_missing fields crafted to throw inside render()
      critical_analysis: null as unknown as Analysis["critical_analysis"],
      reasoning: "x",
      documents_used: [],
      evidence: [],
      sources: [],
      retrieval: { candidate_count: 0, selected_count: 0, selected_documents: [], retrieval_time_ms: 0 },
      ranking: [],
      generated_at: "x",
      provider: "x",
      model: "x",
      bundle_version: 1,
    } as unknown as Analysis;

    render(
      <ErrorBoundary scope="Critical analysis" route="/analyze">
        <AnalysisContent data={poisoned} />
      </ErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/failed to render/i)).toBeInTheDocument();
    restore();
  });
});
