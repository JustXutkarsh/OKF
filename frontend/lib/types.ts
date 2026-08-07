import { z } from "zod";

// Mirrors the backend's frozen contracts. Schemas are permissive
// (passthrough) so additive backend fields never break the frontend.

export const evidenceEntrySchema = z
  .object({
    document_id: z.string(),
    section: z.string(),
    confidence: z.string(),
    matching_score: z.number(),
  })
  .passthrough();

export const reportSourceSchema = z
  .object({
    document_id: z.string(),
    document_title: z.string(),
    source_title: z.string(),
    source_url: z.string(),
    accessed_date: z.string(),
  })
  .passthrough();

export const retrievalDiagnosticsSchema = z
  .object({
    candidate_count: z.number(),
    selected_count: z.number(),
    selected_documents: z.array(z.string()),
    retrieval_time_ms: z.number(),
  })
  .passthrough();

export const rankingEntrySchema = z
  .object({
    document_id: z.string(),
    title_score: z.number(),
    tag_score: z.number(),
    id_score: z.number(),
    resource_score: z.number(),
    phrase_bonus: z.number(),
    total_score: z.number(),
  })
  .passthrough();

export const briefingSchema = z
  .object({
    answer: z.object({
      current_situation: z.string(),
      key_developments: z.array(z.string()),
      key_actors: z.array(z.string()),
    }),
    reasoning: z.string(),
    documents_used: z.array(z.string()),
    evidence: z.array(evidenceEntrySchema),
    sources: z.array(reportSourceSchema),
    retrieval: retrievalDiagnosticsSchema,
    ranking: z.array(rankingEntrySchema),
    generated_at: z.string(),
    provider: z.string(),
    model: z.string(),
  })
  .passthrough();
export type Briefing = z.infer<typeof briefingSchema>;

export const resolvedConflictSchema = z
  .object({
    description: z.string(),
    document_ids: z.array(z.string()),
    supporting_text: z.string(),
    conflicting_text: z.string(),
  })
  .passthrough();

export const analysisSchema = z
  .object({
    critical_analysis: z.object({
      assumptions: z.array(z.string()),
      conflicting_evidence: z.array(resolvedConflictSchema),
      uncertainties: z.array(z.string()),
      alternative_interpretations: z.array(z.string()),
      missing_information: z.array(z.string()),
      confidence_assessment: z.string(),
    }),
    reasoning: z.string(),
    documents_used: z.array(z.string()),
    evidence: z.array(evidenceEntrySchema),
    sources: z.array(reportSourceSchema),
    retrieval: retrievalDiagnosticsSchema,
    ranking: z.array(rankingEntrySchema),
    generated_at: z.string(),
    provider: z.string(),
    model: z.string(),
    bundle_version: z.union([z.number(), z.string(), z.null()]),
  })
  .passthrough();
export type Analysis = z.infer<typeof analysisSchema>;

export const compareSchema = z
  .object({
    question: z.string(),
    generated_at: z.string(),
    briefing: briefingSchema,
    analysis: analysisSchema,
    comparison: z
      .object({
        consumers: z.record(z.string(), z.object({ provider: z.string(), model: z.string() })),
        shared_documents: z.array(z.string()),
        shared_sources: z.array(z.string()),
        bundle_versions: z.record(z.string(), z.union([z.number(), z.string(), z.null()])),
        bundle_versions_agree: z.boolean(),
        durations_ms: z.record(z.string(), z.number()),
      })
      .passthrough(),
  })
  .passthrough();
export type Compare = z.infer<typeof compareSchema>;

export const jobAcceptedSchema = z.object({
  job_id: z.string(),
  job_type: z.string(),
  status: z.string(),
  created_at: z.string(),
});
export type JobAccepted = z.infer<typeof jobAcceptedSchema>;

export const jobRecordSchema = z.object({
  job_id: z.string(),
  job_type: z.string().optional(),
  status: z.string(),
  created_at: z.string().optional(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
  result: z.record(z.string(), z.unknown()).nullable().optional(),
  error: z.record(z.string(), z.string()).nullable().optional(),
});
export type JobRecord = z.infer<typeof jobRecordSchema>;

export const versionResponseSchema = z.object({
  app_version: z.string(),
  git_sha: z.string(),
  build_time: z.string(),
  bundle_version: z.union([z.number(), z.string(), z.null()]),
  components: z.record(z.string(), z.string()),
});
export type VersionResponse = z.infer<typeof versionResponseSchema>;

export const healthResponseSchema = z.object({ status: z.string() });

export const readyResponseSchema = z.object({
  status: z.string(),
  checks: z.object({
    bundle_accessible: z.boolean(),
    registry_loads: z.boolean(),
    document_count: z.number(),
    consumers: z.record(z.string(), z.object({ client_ready: z.boolean() }).passthrough()),
    producer: z.record(z.string(), z.unknown()),
  }),
});
export type ReadyResponse = z.infer<typeof readyResponseSchema>;

export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().optional(),
  }),
});

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}
