import { Badge } from "@/components/ui/badge";

export function MetaFooter({
  provider,
  model,
  generatedAt,
  documentsUsed,
  extra,
}: {
  provider: string;
  model: string;
  generatedAt: string;
  documentsUsed: string[];
  extra?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <Badge variant="secondary">{provider}</Badge>
      <Badge variant="secondary">{model}</Badge>
      {documentsUsed.map((id) => (
        <Badge key={id} variant="outline" className="font-mono">
          {id}
        </Badge>
      ))}
      {extra}
      <span className="ml-auto">generated {new Date(generatedAt).toLocaleString()}</span>
    </div>
  );
}
