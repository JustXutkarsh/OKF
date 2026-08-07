import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import HomePage from "@/app/page";

// The shared single params state now feeds BOTH agents simultaneously —
// one Ask fires /brief AND /analyze in parallel.

const VALID_BRIEF = {
  answer: { current_situation: "Situation.", key_developments: ["d"], key_actors: ["a"] },
  reasoning: "r",
  documents_used: ["d1"],
  evidence: [],
  sources: [],
  retrieval: { candidate_count: 1, selected_count: 1, selected_documents: ["d1"], retrieval_time_ms: 1 },
  ranking: [],
  generated_at: "2026-08-07T00:00:00Z",
  provider: "groq",
  model: "llama",
};

const VALID_ANALYZE = {
  critical_analysis: {
    assumptions: ["a"],
    conflicting_evidence: [],
    uncertainties: [],
    alternative_interpretations: [],
    missing_information: [],
    confidence_assessment: "Assess",
  },
  reasoning: "r",
  documents_used: ["d1"],
  evidence: [],
  sources: [],
  retrieval: { candidate_count: 1, selected_count: 1, selected_documents: ["d1"], retrieval_time_ms: 1 },
  ranking: [],
  generated_at: "2026-08-07T00:00:00Z",
  provider: "groq",
  model: "llama",
  bundle_version: 1,
};

function installFetchMock(calls: string[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      const body = url.includes("/analyze") ? VALID_ANALYZE : VALID_BRIEF;
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    })
  );
}

function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <HomePage />
    </QueryClientProvider>
  );
}

describe("shared question state drives both agents", () => {
  it("one Ask fires BOTH agents in parallel", async () => {
    const calls: string[] = [];
    installFetchMock(calls);
    mount();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/question/i), "Red Sea shipping risks");
    await user.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(
      () => {
        expect(calls.some((c) => c.includes("/brief"))).toBe(true);
        expect(calls.some((c) => c.includes("/analyze"))).toBe(true);
      },
      { timeout: 5000 }
    );
    // The empty state is gone once the question is asked.
    expect(screen.queryByText("Ask a geopolitical question")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("both agents render their reports — and Debate mode combines them", async () => {
    const calls: string[] = [];
    installFetchMock(calls);
    mount();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/question/i), "NATO posture");
    await user.click(screen.getByRole("button", { name: /^ask$/i }));

    // Both agent panels reach their reports.
    expect(
      (await screen.findAllByText("Current Situation", undefined, { timeout: 10000 })).length
    ).toBeGreaterThan(0);
    expect(
      (await screen.findAllByText("Confidence Assessment", undefined, { timeout: 10000 })).length
    ).toBeGreaterThan(0);

    // Switch to Debate: interleaved argument appears.
    await user.click(screen.getByRole("button", { name: /debate/i }));
    expect(await screen.findByText(/Briefing says · Current situation/i)).toBeInTheDocument();
    expect(await screen.findByText(/Critic responds · Confidence assessment/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
