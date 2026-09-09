export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-border bg-surface shadow-sm ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function KpiCard({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}
