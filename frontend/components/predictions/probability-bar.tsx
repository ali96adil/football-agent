interface ProbabilityBarProps {
  label: string;
  value: number;
}

export function ProbabilityBar({
  label,
  value,
}: ProbabilityBarProps) {
  const percent = Math.round(value * 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>

        <span className="text-muted-foreground">
          {percent}%
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{
            width: `${percent}%`,
          }}
        />
      </div>
    </div>
  );
}
