"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ChevronDown, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const POLL_MS = 1500;

export function UpdateKnowledge() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [conceptId, setConceptId] = useState("");
  const [dryRun, setDryRun] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.producerUpdate(conceptId.trim(), dryRun),
    onSuccess: (accepted) => setJobId(accepted.job_id),
  });

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) =>
      query.state.data && ["succeeded", "failed"].includes(query.state.data.status)
        ? false
        : POLL_MS,
  });

  const status = jobId ? job.data?.status ?? "pending" : null;
  const record = job.data;

  function reset() {
    mutation.reset();
    setJobId(null);
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 rounded border border-border/50 bg-muted/30 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-muted-foreground transition-colors hover:border-border hover:text-foreground"
      >
        <RefreshCw
          className={`size-3 ${jobId && status !== "succeeded" && status !== "failed" ? "animate-spin" : ""}`}
        />
        <span className="hidden sm:inline">SYNC BUNDLE</span>
        <ChevronDown
          className={`size-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-40 mt-2 w-80"
          >
            <div className="terminal-window rounded-xl border border-border/60 shadow-xl">
              <div className="flex items-center gap-2 border-b border-border/40 px-4 py-2.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
                  SYNC BUNDLE
                </span>
              </div>
              <div className="space-y-3 p-4">
                <p className="text-xs text-muted-foreground">
                  Queue a producer run for one tracked concept; the job runs asynchronously.
                </p>
                <div className="space-y-1.5">
                  <Label htmlFor="concept-id" className="text-xs">
                    Concept ID
                  </Label>
                  <Input
                    id="concept-id"
                    placeholder="e.g. us-china-tariffs"
                    value={conceptId}
                    onChange={(event) => setConceptId(event.target.value)}
                  />
                </div>
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(event) => setDryRun(event.target.checked)}
                  />
                  Dry run (validate only, write nothing)
                </label>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    disabled={!conceptId.trim() || mutation.isPending}
                    onClick={() => {
                      reset();
                      mutation.mutate();
                    }}
                  >
                    {mutation.isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                    Queue update
                  </Button>
                  {jobId && (
                    <Button size="sm" variant="ghost" onClick={reset}>
                      Reset
                    </Button>
                  )}
                </div>

                {mutation.isError && (
                  <p className="text-xs text-destructive">
                    {mutation.error instanceof Error ? mutation.error.message : "Failed to queue job."}
                  </p>
                )}

                {jobId && (
                  <div className="space-y-2 border-t pt-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {jobId.slice(0, 8)}…
                      </span>
                      <Badge
                        variant={
                          status === "succeeded"
                            ? "success"
                            : status === "failed"
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        {status}
                      </Badge>
                    </div>
                    {(status === "pending" || status === "running") && (
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
                      </div>
                    )}
                    {status === "succeeded" && record?.result && (
                      <div className="flex items-start gap-1.5">
                        <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-500" />
                        <p className="whitespace-pre-wrap text-muted-foreground">
                          {String(record.result.report ?? "Update completed.")}
                        </p>
                      </div>
                    )}
                    {status === "failed" && record?.error && (
                      <div className="flex items-start gap-1.5">
                        <XCircle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
                        <p className="text-destructive">
                          {record.error.code}: {record.error.message}
                        </p>
                      </div>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 text-xs"
                      onClick={() => queryClient.invalidateQueries({ queryKey: ["job", jobId] })}
                    >
                      Refresh status
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
