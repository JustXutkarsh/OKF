"use client";

/**
 * Global error boundary — last-resort handler for errors in the root
 * layout itself (cannot rely on app-wide UI being alive, so it renders
 * its own <html>/<body> with inline styles only).
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          display: "flex",
          minHeight: "100vh",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          gap: "1rem",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Something went wrong</h1>
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
          {error?.message || "An unexpected error occurred."}
        </p>
        {error?.digest && (
          <p style={{ color: "#9ca3af", fontSize: "0.75rem" }}>request_id: {error.digest}</p>
        )}
        <button
          type="button"
          onClick={reset}
          style={{
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            padding: "0.375rem 0.75rem",
            fontSize: "0.875rem",
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
