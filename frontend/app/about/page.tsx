import { TopNav } from "@/components/top-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const PILLARS = [
  {
    title: "Portable knowledge",
    body: "The okf/ bundle is plain markdown + YAML frontmatter: human-readable, git-diffable, and consumable by any agent with zero SDK or vendor lock-in.",
  },
  {
    title: "Independent agents",
    body: "Producer, Consumer A, and Consumer B share no code, no database, and no LLM provider. They exchange ground truth exclusively through the bundle.",
  },
  {
    title: "Deterministic grounding",
    body: "Retrieval is lexical, evidence and sources are assembled in Python, and the LLM is constrained to reasoning only. Every claim traces to a source and a commit.",
  },
];

const STACK = [
  ["Producer", "Python · Tavily · provider-configurable LLM"],
  ["Consumer A", "Python · briefing agent (read-only)"],
  ["Consumer B", "Python · critical analysis agent (read-only)"],
  ["Backend", "FastAPI · jobs · auth · rate limits · metrics"],
  ["Frontend", "Next.js 15 · TypeScript · Tailwind · TanStack Query"],
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">About this project</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Cross-Agent OKF Knowledge Exchange — a geopolitics briefing system proving that
            knowledge can be portable, auditable, and shared between fully independent AI agents.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {PILLARS.map((pillar) => (
            <Card key={pillar.title}>
              <CardHeader>
                <CardTitle className="text-base">{pillar.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{pillar.body}</CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>System overview</CardTitle>
            <CardDescription>
              The bundle is the only shared artifact; every other component is independent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y text-sm">
              {STACK.map(([name, value]) => (
                <div key={name} className="flex items-center justify-between py-2">
                  <span className="font-medium">{name}</span>
                  <span className="text-muted-foreground">{value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
