"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Search } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const formSchema = z.object({
  question: z.string().min(1, "Enter a question.").max(2000),
  maxDocs: z.number().int().min(1).max(10),
});

export type QuestionParams = z.infer<typeof formSchema>;

export function QuestionForm({
  onSubmit,
  loading,
}: {
  onSubmit: (params: QuestionParams) => void;
  loading: boolean;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<QuestionParams>({
    resolver: zodResolver(formSchema),
    defaultValues: { question: "", maxDocs: 3 },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3 md:flex-row md:items-end">
      <div className="flex-1 space-y-1.5">
        <Label htmlFor="question">Question</Label>
        <Input
          id="question"
          placeholder="e.g. How reliable is the picture of NATO posture and the Ukraine frontline?"
          autoComplete="off"
          {...register("question")}
        />
        {errors.question && <p className="text-xs text-destructive">{errors.question.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="maxDocs">Max documents</Label>
        <select
          id="maxDocs"
          className="flex h-9 w-24 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          {...register("maxDocs", { valueAsNumber: true })}
        >
          {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
      <Button type="submit" disabled={loading} className="md:mb-px">
        {loading ? <Loader2 className="animate-spin" /> : <Search />}
        {loading ? "Working…" : "Ask"}
      </Button>
    </form>
  );
}
