import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/types";

export function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
          {action}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm leading-relaxed">{children}</CardContent>
    </Card>
  );
}

export function ListSection({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="text-muted-foreground">None found.</p>;
  return (
    <ul className="list-disc space-y-1.5 pl-5">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

export function ErrorCard({ error }: { error: unknown }) {
  const code = error instanceof ApiError ? error.code : `ERROR`;
  const message = error instanceof Error ? error.message : "Request failed.";
  return (
    <Card className="border-destructive/40">
      <CardContent className="space-y-1 p-4">
        <p className="text-sm font-semibold text-destructive">{code}</p>
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}

export function LoadingColumns() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[0, 1].map((card) => (
        <Card key={card}>
          <CardHeader>
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-2/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function EmptyPrompt({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
      {label}
    </div>
  );
}
