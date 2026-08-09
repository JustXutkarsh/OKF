"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Send, ChevronDown } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const formSchema = z.object({
  question: z.string().min(1, "Enter a query.").max(2000),
  maxDocs: z.number().int().min(1).max(10),
});

export type QuestionParams = z.infer<typeof formSchema>;

const EXAMPLE_QUERIES = [
  "What is the current state of the Ukraine-Russia conflict?",
  "How reliable is NATO's eastern flank posture?",
  "What are the latest China-Taiwan tensions?",
  "Assess US-China trade war developments.",
];

export function QuestionForm({
  onSubmit,
  loading,
}: {
  onSubmit: (params: QuestionParams) => void;
  loading: boolean;
}) {
  const [showExamples, setShowExamples] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<QuestionParams>({
    resolver: zodResolver(formSchema),
    defaultValues: { question: "", maxDocs: 3 },
  });

  const question = watch("question");

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        {/* Terminal prompt row */}
        <div className="flex items-stretch gap-2">
          <div className="flex flex-1 items-center gap-2 rounded-lg border border-border/60 bg-card/60 px-3 py-2.5 focus-within:border-border transition-colors">
            <span className="shrink-0 font-mono text-[11px] text-muted-foreground/60 select-none">
              QUERY://
            </span>
            <label htmlFor="question" className="sr-only">Geopolitical Question</label>
            <input
              id="question"
              placeholder="Enter geopolitical intelligence query…"
              autoComplete="off"
              className="flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none"
              {...register("question")}
            />
            {question && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="terminal-cursor shrink-0"
                style={{ "--agent-color": "hsl(var(--agent-brief))" } as React.CSSProperties}
              />
            )}
          </div>

          {/* Max docs */}
          <div className="flex items-center gap-1.5 rounded-lg border border-border/60 bg-card/60 px-3">
            <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/60 whitespace-nowrap">
              DOCS
            </span>
            <select
              id="maxDocs"
              className="w-8 bg-transparent font-mono text-sm text-foreground focus:outline-none"
              {...register("maxDocs", { valueAsNumber: true })}
            >
              {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          {/* Submit */}
          <motion.button
            type="submit"
            aria-label="Ask"
            disabled={loading}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-2 rounded-lg border border-border/60 bg-foreground/5 px-4 py-2.5 font-mono text-[11px] uppercase tracking-widest text-foreground transition-all hover:bg-foreground/10 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Send className="size-3.5" />
            )}
            <span className="hidden sm:inline">
              {loading ? "DISPATCHING" : "DISPATCH"}
            </span>
          </motion.button>
        </div>

        {errors.question && (
          <p className="font-mono text-[10px] text-destructive">{errors.question.message}</p>
        )}
      </form>

      {/* Example queries */}
      <div>
        <button
          type="button"
          onClick={() => setShowExamples((v) => !v)}
          className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground/50 transition-colors hover:text-muted-foreground"
        >
          <ChevronDown
            className={`size-3 transition-transform ${showExamples ? "rotate-180" : ""}`}
          />
          EXAMPLE QUERIES
        </button>
        <AnimatePresence>
          {showExamples && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2 overflow-hidden"
            >
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      setValue("question", q);
                      setShowExamples(false);
                    }}
                    className="rounded border border-border/40 bg-muted/30 px-2.5 py-1 text-left font-mono text-[10px] text-muted-foreground transition-colors hover:border-border/80 hover:text-foreground"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
