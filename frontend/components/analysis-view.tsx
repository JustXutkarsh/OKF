"use client";

import type { Analysis } from "@/lib/types";
import { ConfidenceViz } from "@/components/confidence-viz";
import { Reveal, StaggerGroup } from "@/components/reveal";
import { Typewriter } from "@/components/typewriter";
import { DossierSection, IntelItem, IntelAlert } from "@/components/dossier-section";

const NOT_COVERED = "This topic is not covered";

export function AnalysisContent({ data }: { data: Analysis }) {
  const analysis = data.critical_analysis;

  if (analysis.confidence_assessment.startsWith(NOT_COVERED)) {
    return (
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm">
        <p className="font-mono text-[10px] uppercase tracking-widest text-amber-500/80 mb-2">
          NO COVERAGE
        </p>
        <p className="text-foreground/80">{analysis.confidence_assessment}</p>
      </div>
    );
  }

  return (
    <StaggerGroup className="space-y-4 max-w-3xl">
      {/* Confidence Verdict */}
      <Reveal>
        <DossierSection
          title="CONFIDENCE VERDICT"
          classification="CRITICAL"
          accentColor="hsl(var(--agent-analysis))"
        >
          <div className="max-w-2xl text-[14px] leading-relaxed text-foreground/90">
            <Typewriter text={analysis.confidence_assessment} />
          </div>
        </DossierSection>
      </Reveal>

      {/* Assumptions Challenged */}
      <Reveal>
        <DossierSection
          title="ASSUMPTIONS CHALLENGED"
          classification="CONTESTED"
          accentColor="hsl(var(--terminal-amber) / 0.6)"
          action={
            <span className="font-mono text-[10px] text-muted-foreground/40">
              {analysis.assumptions.length} FLAGGED
            </span>
          }
        >
          {analysis.assumptions.length === 0 ? (
            <p className="text-sm text-muted-foreground/60">No assumptions flagged.</p>
          ) : (
            <div className="space-y-2">
              {analysis.assumptions.map((item, i) => (
                <IntelAlert key={i} text={item} kind="warning" />
              ))}
            </div>
          )}
        </DossierSection>
      </Reveal>

      {/* Uncertainties */}
      <Reveal>
        <DossierSection
          title="UNCERTAINTIES"
          classification="UNCERTAIN"
          accentColor="hsl(var(--terminal-amber) / 0.4)"
          action={
            <span className="font-mono text-[10px] text-muted-foreground/40">
              {analysis.uncertainties.length} FLAGGED
            </span>
          }
        >
          {analysis.uncertainties.length === 0 ? (
            <p className="text-sm text-muted-foreground/60">No uncertainties flagged.</p>
          ) : (
            <div className="space-y-2">
              {analysis.uncertainties.map((item, i) => (
                <IntelItem
                  key={i}
                  index={i}
                  text={item}
                  color="hsl(var(--terminal-amber) / 0.6)"
                />
              ))}
            </div>
          )}
        </DossierSection>
      </Reveal>

      {/* Conflicting Intelligence */}
      <Reveal>
        <DossierSection
          title="CONFLICTING INTELLIGENCE"
          classification="CONTESTED"
          accentColor="hsl(var(--terminal-red) / 0.5)"
          action={
            <span className="font-mono text-[10px] text-muted-foreground/40">
              {analysis.conflicting_evidence.length} CONFLICTS
            </span>
          }
        >
          {analysis.conflicting_evidence.length === 0 ? (
            <p className="text-sm text-muted-foreground/60">
              No verifiable conflicts found in retrieved documents.
            </p>
          ) : (
            <div className="space-y-3">
              {analysis.conflicting_evidence.map((conflict, index) => (
                <div key={index} className="rounded border border-border/40 bg-background/30 p-3">
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-muted-foreground/70">
                    {conflict.description}
                  </p>
                  <p className="mb-2 font-mono text-[9px] text-muted-foreground/50">
                    DOCS: {conflict.document_ids.join(", ")}
                  </p>
                  <div className="space-y-2">
                    <blockquote className="border-l-2 border-emerald-500/50 pl-3 text-sm text-foreground/80">
                      <span className="mb-1 block font-mono text-[9px] text-emerald-500/60">
                        SUPPORTING
                      </span>
                      {conflict.supporting_text}
                    </blockquote>
                    <blockquote className="border-l-2 border-red-500/50 pl-3 text-sm text-foreground/80">
                      <span className="mb-1 block font-mono text-[9px] text-red-500/60">
                        CONFLICTING
                      </span>
                      {conflict.conflicting_text}
                    </blockquote>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DossierSection>
      </Reveal>

      {/* Alternative Interpretations & Gaps */}
      <Reveal>
        <div className="grid gap-3 sm:grid-cols-2">
          <DossierSection
            title="ALTERNATIVE INTERPRETATIONS"
            accentColor="hsl(var(--terminal-cyan) / 0.4)"
            action={
              <span className="font-mono text-[10px] text-muted-foreground/40">
                {analysis.alternative_interpretations.length}
              </span>
            }
          >
            {analysis.alternative_interpretations.length === 0 ? (
              <p className="text-sm text-muted-foreground/60">None identified.</p>
            ) : (
              <div className="space-y-2">
                {analysis.alternative_interpretations.map((item, i) => (
                  <IntelAlert key={i} text={item} kind="info" />
                ))}
              </div>
            )}
          </DossierSection>

          <DossierSection
            title="INTELLIGENCE GAPS"
            classification="GAP"
            accentColor="hsl(var(--terminal-red) / 0.3)"
            action={
              <span className="font-mono text-[10px] text-muted-foreground/40">
                {analysis.missing_information.length}
              </span>
            }
          >
            {analysis.missing_information.length === 0 ? (
              <p className="text-sm text-muted-foreground/60">No gaps identified.</p>
            ) : (
              <div className="space-y-2">
                {analysis.missing_information.map((item, i) => (
                  <IntelAlert key={i} text={item} kind="danger" />
                ))}
              </div>
            )}
          </DossierSection>
        </div>
      </Reveal>

      {/* Evidence Confidence */}
      <Reveal>
        <DossierSection
          title="EVIDENCE CONFIDENCE"
          classification="RESTRICTED"
          accentColor="hsl(var(--terminal-amber) / 0.4)"
        >
          <ConfidenceViz evidence={data.evidence} />
        </DossierSection>
      </Reveal>
    </StaggerGroup>
  );
}
