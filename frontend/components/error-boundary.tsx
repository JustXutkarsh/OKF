"use client";

import { diagnosticsContext, describeDiagnostics } from "@/lib/diagnostics";
import { reportError } from "@/lib/monitoring";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Component, type ReactNode } from "react";

/**
 * Local error boundary. Wraps a single view/panel so a render-time
 * exception there shows an error card and can NOT blank or take down
 * the rest of the application. Reports to lib/monitoring with the
 * route diagnostics so operators can correlate failure ↔ API response.
 *
 * Usage:
 *   <ErrorBoundary scope="analysis" route="/analyze">
 *     <AnalysisContent data={data} />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<
  {
    /** Human label for the failed region, e.g. "Critical analysis". */
    scope: string;
    /** API route that produced the data being rendered. */
    route: string;
    children: ReactNode;
  },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    reportError(error, {
      component: this.props.scope,
      ...diagnosticsContext(this.props.route),
    });
    console.warn(
      `[okf:error-boundary] ${this.props.scope} failed to render:`,
      describeDiagnostics(this.props.route),
      info
    );
  }

  private reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="rounded-xl border border-destructive/40 bg-destructive/5 p-6 text-sm"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
            <div className="flex-1 space-y-1">
              <p className="font-semibold text-destructive">
                {this.props.scope} failed to render
              </p>
              <p className="text-muted-foreground">
                {this.state.error.message || "An unexpected rendering error occurred."}
              </p>
              <p className="text-xs text-muted-foreground/80">
                {describeDiagnostics(this.props.route)}
              </p>
              <button
                type="button"
                onClick={this.reset}
                className="mt-2 inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-muted"
              >
                <RotateCcw className="size-3" /> Retry render
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
