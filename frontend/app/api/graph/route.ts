import { NextResponse } from "next/server";
import { loadBundleGraph } from "@/lib/knowledge-graph";
import bundleGraphData from "@/lib/bundle-graph.json";

// Read-only knowledge graph scan of the local OKF bundle with validated fallback.
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const graph = loadBundleGraph();
    if (graph.nodes.length > 0) {
      return NextResponse.json(graph, { status: 200 });
    }
    return NextResponse.json(bundleGraphData, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { ...bundleGraphData, errors: [String(error)] },
      { status: 200 }
    );
  }
}
