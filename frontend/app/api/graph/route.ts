import { NextResponse } from "next/server";
import { loadBundleGraph } from "@/lib/knowledge-graph";

// Read-only knowledge graph scan of the local OKF bundle. Fresh each call.
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const graph = loadBundleGraph();
    return NextResponse.json(graph, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { nodes: [], edges: [], errors: [String(error)] },
      { status: 200 }
    );
  }
}
