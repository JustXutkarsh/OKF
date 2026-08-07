"use client";

import type { Briefing } from "@/lib/types";
import { ConfidenceViz } from "@/components/confidence-viz";
import { EvidenceGallery } from "@/components/evidence-card";
import { MetaFooter } from "@/components/meta-footer";
import { Reveal, StaggerGroup } from "@/components/reveal";
import { Typewriter } from "@/components/typewriter";
import { ListSection, SectionCard } from "@/components/section-card";
import { SourcesList } from "@/components/sources-list";
import { FileText, Newspaper, Users } from "lucide-react";

const NOT_COVERED = "This topic is not covered";

/**
 * Evidence-first briefing report. Reveal order communicates method:
 * evidence before synthesis, sources always last. Sections stagger in;
 * the situation lead types into place.
 */
export function BriefingContent({ data }: { data: Briefing }) {
  if (data.answer.current_situation.startsWith(NOT_COVERED)) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 text-sm">
        <p className="font-medium">{data.answer.current_situation}</p>
        <p className="mt-1 text-muted-foreground">
          Try a topic covered by the bundle (conflicts, economics, actors, policy).
        </p>
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
          title="Current Situation"
          action={<FileText className="size-4 text-muted-foreground" />}
        >
          <p className="text-[15px] leading-relaxed">
            <Typewriter text={data.answer.current_situation} />
          </p>
        </SectionCard>
      </Reveal>

      <Reveal>
        <div className="grid gap-4 md:grid-cols-2">
          <SectionCard
            title="Key Developments"
            action={<Newspaper className="size-4 text-muted-foreground" />}
          >
            <ListSection items={data.answer.key_developments} />
          </SectionCard>
          <SectionCard title="Key Actors" action={<Users className="size-4 text-muted-foreground" />}>
            <ListSection items={data.answer.key_actors} />
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
