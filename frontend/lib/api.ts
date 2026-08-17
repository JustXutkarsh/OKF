import { loadConfig } from "@/lib/config";
import { recordDiagnostics } from "@/lib/diagnostics";
import {
  ApiError,
  analysisSchema,
  briefingSchema,
  compareSchema,
  errorEnvelopeSchema,
  healthResponseSchema,
  jobAcceptedSchema,
  jobRecordSchema,
  readyResponseSchema,
  versionResponseSchema,
  type Analysis,
  type Briefing,
  type Compare,
  type JobAccepted,
  type JobRecord,
  type ReadyResponse,
  type VersionResponse,
} from "@/lib/types";
import type { z } from "zod";

const API_PREFIX = "/api/v1";

function normalizeBaseUrl(raw: string): string {
  // Tolerate common config slips: trailing slashes or a pre-appended
  // "/api/v1" segment. The prefix is applied exactly once below.
  let url = raw.trim().replace(/\/+$/, "");
  if (url.toLowerCase().endsWith(API_PREFIX)) {
    url = url.slice(0, -API_PREFIX.length);
  }
  return url;
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  schema: z.ZodType<T>,
  body?: unknown
): Promise<T> {
  const { baseUrl: rawBaseUrl, apiKey } = loadConfig();
  const baseUrl = normalizeBaseUrl(rawBaseUrl);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

  const finalUrl = `${baseUrl}${API_PREFIX}${path}`;
  const startedAt = performance.now();

  let response: Response;
  try {
    response = await fetch(finalUrl, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", `Cannot reach backend at ${baseUrl}.`, 0);
  }

  const text = await response.text();
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError("INVALID_RESPONSE", "Backend returned non-JSON response.", response.status);
  }

  if (!response.ok) {
    if (path === "/ready") {
      const parsedReady = readyResponseSchema.safeParse(payload);
      if (parsedReady.success) {
        recordDiagnostics(path, Math.round(performance.now() - startedAt), payload);
        return parsedReady.data as T;
      }
    }
    const parsedError = errorEnvelopeSchema.safeParse(payload);
    if (parsedError.success) {
      throw new ApiError(parsedError.data.error.code, parsedError.data.error.message, response.status);
    }
    throw new ApiError("HTTP_ERROR", `Request failed with status ${response.status}.`, response.status);
  }
  const parsed = schema.parse(payload);
  // Record diagnostics only for a payload that passed the contract —
  // a malformed body must never masquerade as a successful request.
  recordDiagnostics(path, Math.round(performance.now() - startedAt), payload);
  return parsed;
}

export const api = {
  brief: (question: string, maxDocs?: number): Promise<Briefing> =>
    request("POST", "/brief", briefingSchema, { question, max_docs: maxDocs ?? null }),

  analyze: (question: string, maxDocs?: number): Promise<Analysis> =>
    request("POST", "/analyze", analysisSchema, { question, max_docs: maxDocs ?? null }),

  compare: (question: string, maxDocs?: number): Promise<Compare> =>
    request("POST", "/compare", compareSchema, { question, max_docs: maxDocs ?? null }),

  producerUpdate: (conceptId: string, dryRun = false): Promise<JobAccepted> =>
    request("POST", "/producer/update", jobAcceptedSchema, {
      concept_id: conceptId,
      dry_run: dryRun,
    }),

  getJob: (jobId: string): Promise<JobRecord> =>
    request("GET", `/jobs/${jobId}`, jobRecordSchema),

  getHealth: () => request("GET", "/health", healthResponseSchema),

  getReady: (): Promise<ReadyResponse> => request("GET", "/ready", readyResponseSchema),

  getVersion: (): Promise<VersionResponse> => request("GET", "/version", versionResponseSchema),
};
