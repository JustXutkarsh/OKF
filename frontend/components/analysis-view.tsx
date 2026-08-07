"use client";

import type { Analysis } from "@/lib/types";
import { ConfidenceViz } from "@/components/confidence-viz";
import { EvidenceGallery } from "@/components/evidence-card";
import { MetaFooter } from "@/components/meta-footer";
import { Reveal, StaggerGroup } from "@/components/reveal";
import { SectionCard, ListSection } from "@/components/section-card";
import { SourcesList } from "@/components/sources-list";
import { Typewriter } from "@/components/typewriter";
import { AlertTriangle, CircleHelp, Lightbulb, Scale, ShieldAlert } from "lucide-react";

const NOT_COVERED = "This topic is not covered";

/**
 * Evidence-first critical analysis. The adversarial voice surfaces last —
 * its content (assumptions, gaps, conflicts) is the agent's *verdict*,
 * so the evidence gallery and the typed confidence statement lead.
 */
export function AnalysisContent({ data }: { data: Analysis }) {
  const analysis = data.critical_analysis;

  if (analysis.confidence_assessment.startsWith(NOT_COVERED)) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 text-sm">
        <p className="font-medium">{analysis.confidence_assessment}</p>
      </div>
    );
  }
  return (
    <StaggerGroup className="grid gap-4">
      <Reveal>
        <SectionCard
          title="Retrieved Evidence"
          action={
            <span className="font-mono text-xs text-muted-foreground">
              {data.evidence.length} fragments
            </span>
          }
        >
          <EvidenceGallery evidence={data.evidence} sources={data.sources} />
        </SectionCard>
      </Reveal>

      <Reveal>
        <SectionCard
          title="Confidence Assessment"
          action={<ShieldAlert className="size-4 text-muted-foreground" />}
        >
          <p className="text-[15px] leading-relaxed">
            <Typewriter text={analysis.confidence_assessment} />
          </p>
        </SectionCard>
      </Reveal>

      <Reveal>
        <div className="grid gap-4 md:grid-cols-2">
          <SectionCard title="Assumptions" action={<CircleHelp className="size-4 text-muted-foreground" />}>
            <ListSection items={analysis.assumptions} />
          </SectionCard>
          <SectionCard title="Uncertainties" action={<AlertTriangle className="size-4 text-muted-foreground" />}>
            <ListSection items={analysis.uncertainties} />
          </SectionCard>
        </div>
      </Reveal>

      <Reveal>
        <SectionCard title="Conflicting Evidence" action={<Scale className="size-4 text-muted-foreground" />}>
          {analysis.conflicting_evidence.length === 0 ? (
            <p className="text-muted-foreground">No verifiable conflicts found in the retrieved documents.</p>
          ) : (
            <div className="space-y-4">
              {analysis.conflicting_evidence.map((conflict, index) => (
                <div key={index} className="rounded-lg border p-3">
                  <p className="mb-2 font-medium">{conflict.description}</p>
                  <p className="text-xs text-muted-foreground">
                    Documents: {conflict.document_ids.join(", ")}
                  </p>
                  <blockquote className="mt-2 border-l-2 border-emerald-500/60 pl-3 text-sm">
                    {conflict.supporting_text}
                  </blockquote>
                  <blockquote className="mt-2 border-l-2 border-destructive/60 pl-3 text-sm">
                    {conflict.conflicting_text}
                  </blockquote>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </Reveal>

      <Reveal>
        <div className="grid gap-4 md:grid-cols-2">
          <SectionCard title="Alternative Interpretations" action={<Lightbulb className="size-4 text-muted-foreground" />}>
            <ListSection items={analysis.alternative_interpretations} />
          </SectionCard>
          <SectionCard title="Missing Information">
            <ListSection items={analysis.missing_information} />
          </SectionCard>
        </div>
      </Reveal>

      <Reveal>
        <SectionCard title="Confidence Breakdown">
          <ConfidenceViz evidence={data.evidence} />
        </SectionCard>
      </Reveal>

      <Reveal>
        <SectionCard title="Sources">
          <SourcesList sources={data.sources} />
        </SectionCard>
      </Reveal>

      <Reveal>
        <MetaFooter
          provider={data.provider}
          model={data.model}
          generatedAt={data.generated_at}
          documentsUsed={data.documents_used}
        />
      </Reveal>
    </StaggerGroup>
  );
}
