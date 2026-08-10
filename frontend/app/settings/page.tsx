"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, PlugZap, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "@/lib/api";
import { DEFAULT_CONFIG, loadConfig, saveConfig } from "@/lib/config";
import { ApiError } from "@/lib/types";
import { TopNav } from "@/components/top-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const settingsSchema = z.object({
  baseUrl: z.string().url("Enter a valid URL, e.g. http://localhost:8000"),
  apiKey: z.string(),
});
type SettingsForm = z.infer<typeof settingsSchema>;

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span>{label}</span>
      <span className="flex items-center gap-1.5">
        {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
        {ok ? (
          <CheckCircle2 className="size-4 text-emerald-500" />
        ) : (
          <XCircle className="size-4 text-destructive" />
        )}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<SettingsForm>({
    resolver: zodResolver(settingsSchema),
    defaultValues: DEFAULT_CONFIG,
  });

  useEffect(() => {
    reset(loadConfig());
  }, [reset]);

  const version = useQuery({ queryKey: ["version"], queryFn: api.getVersion, retry: 1 });
  const ready = useQuery({ queryKey: ["ready"], queryFn: api.getReady, retry: 1 });

  const connectionError =
    (version.error instanceof ApiError && version.error) ||
    (ready.error instanceof ApiError && ready.error) ||
    null;

  const [testState, setTestState] = useState<"idle" | "testing" | "ok" | "error">("idle");

  async function runConnectionTest() {
    setTestState("testing");
    const [versionResult, readyResult] = await Promise.allSettled([
      version.refetch(),
      ready.refetch(),
    ]);
    const ok =
      versionResult.status === "fulfilled" &&
      readyResult.status === "fulfilled" &&
      !versionResult.value.error &&
      !readyResult.value.error &&
      Boolean(readyResult.value.data?.status);
    setTestState(ok ? "ok" : "error");
  }

  function handleSave(values: SettingsForm) {
    saveConfig(values);
    reset(values);
    queryClient.invalidateQueries({ queryKey: ["ready"] });
    queryClient.invalidateQueries({ queryKey: ["version"] });
  }

  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Backend connection, authentication, and system status.
          </p>
        </div>

        <form
          onSubmit={handleSubmit(handleSave)}
          className="space-y-4"
        >
          <Card>
            <CardHeader>
              <CardTitle>Backend connection</CardTitle>
              <CardDescription>Stored locally in your browser only.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="baseUrl">Base URL</Label>
                <Input id="baseUrl" placeholder="http://localhost:8000" {...register("baseUrl")} />
                {errors.baseUrl && (
                  <p className="text-xs text-destructive">{errors.baseUrl.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="apiKey">API key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="Leave empty when backend auth is disabled"
                  autoComplete="off"
                  {...register("apiKey")}
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={!isDirty}>
                  Save
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={testState === "testing"}
                  onClick={runConnectionTest}
                >
                  {testState === "testing" ? <Loader2 className="animate-spin" /> : <PlugZap />}
                  {testState === "testing" ? "Testing…" : "Test connection"}
                </Button>
              </div>
              {testState === "ok" && (
                <p className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="size-4" /> Connection OK — version and readiness
                  refreshed.
                </p>
              )}
              {(testState === "error" || (connectionError && testState === "idle")) && (
                <p className="text-sm text-destructive">
                  {connectionError
                    ? `${connectionError.code}: ${connectionError.message}`
                    : "Connection test failed."}
                </p>
              )}
            </CardContent>
          </Card>
        </form>

        <Card>
          <CardHeader>
            <CardTitle>System status</CardTitle>
            <CardDescription>Live readiness report from the backend.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {ready.isPending && <Loader2 className="size-4 animate-spin" />}
            {ready.data && (
              <>
                <StatusRow
                  label="Overall"
                  ok={ready.data.status === "ready" || ready.data.status === "ok"}
                  detail={ready.data.status}
                />
                <StatusRow label="Bundle accessible" ok={ready.data.checks.bundle_accessible} />
                <StatusRow label="Producer registry" ok={ready.data.checks.registry_loads} />
                <StatusRow
                  label="Documents in bundle"
                  ok={ready.data.checks.document_count > 0}
                  detail={String(ready.data.checks.document_count)}
                />
                {Object.entries(ready.data.checks.consumers).map(([name, info]) => (
                  <StatusRow key={name} label={`Consumer: ${name}`} ok={info.client_ready} />
                ))}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Version</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {version.isPending && <Loader2 className="size-4 animate-spin" />}
            {version.data && (
              <>
                <div className="flex items-center justify-between text-sm">
                  <span>Backend app</span>
                  <Badge variant="secondary">{version.data.app_version}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Bundle schema</span>
                  <Badge variant="secondary">{String(version.data.bundle_version)}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Git SHA</span>
                  <span className="font-mono text-xs">{version.data.git_sha}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Build time</span>
                  <span className="text-xs text-muted-foreground">{version.data.build_time}</span>
                </div>
                {Object.entries(version.data.components).map(([name, value]) => (
                  <div key={name} className="flex items-center justify-between text-sm">
                    <span>{name}</span>
                    <Badge variant="outline">{value}</Badge>
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
