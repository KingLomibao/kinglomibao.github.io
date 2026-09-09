"use client";

// Renders the *structured* data a Kinvera tool returned, independent
// of whatever the assistant's prose says about it. This is the
// deliberate safety mechanism behind "AI explains, business rules
// decide": even if the assistant's text were ever wrong, the badges
// and tables here are built directly from the tool's own JSON, not
// parsed out of the assistant's sentence.

import { Badge, SeverityBadge, StaffingStatusBadge } from "@/components/Badge";

type ToolResult = Record<string, unknown>;

function EmployeeChip({ full_name, role, site }: { full_name: string; role?: string | null; site?: string | null }) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
      <span className="font-medium text-foreground">{full_name}</span>
      {role && <span className="ml-2 text-muted">{role}</span>}
      {site && <span className="ml-1 text-muted">· {site}</span>}
    </div>
  );
}

function RuleChecklist({ checks }: { checks: { rule: string; passed: boolean; reason: string | null }[] }) {
  return (
    <ul className="mt-2 space-y-1 rounded-md bg-gray-50 p-3 text-xs">
      {checks.map((check) => (
        <li key={check.rule} className="flex items-start gap-2">
          <span className={check.passed ? "text-emerald-700" : "text-red-700"}>{check.passed ? "✓" : "✗"}</span>
          <span className="text-muted">
            <span className="font-mono text-[11px] text-foreground">{check.rule}</span>
            {check.reason ? <> — {check.reason}</> : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

function AmbiguousNotice({ result }: { result: ToolResult }) {
  const candidates = (result.candidates as { id: number; full_name?: string; name?: string; role?: string; site?: string; location?: string }[]) ?? [];
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
      <p className="mb-2 font-medium">More than one match - clarification needed</p>
      <div className="space-y-1">
        {candidates.map((c) => (
          <div key={c.id} className="text-xs">
            {c.full_name ?? c.name}
            {c.role && ` · ${c.role}`}
            {c.site && ` · ${c.site}`}
            {c.location && ` · ${c.location}`}
          </div>
        ))}
      </div>
    </div>
  );
}

function NotFoundOrErrorNotice({ result }: { result: ToolResult }) {
  return (
    <div className="rounded-md border border-border bg-gray-50 p-3 text-sm text-muted">
      {(result.message as string) ?? "No matching record was found."}
    </div>
  );
}

function EligibilityCard({ result }: { result: ToolResult }) {
  const eligible = result.eligible as boolean;
  return (
    <div className="rounded-md border border-border bg-surface p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-medium text-foreground">{result.employee_name as string}</span>
        <Badge tone={eligible ? "positive" : "critical"}>{eligible ? "eligible" : "not eligible"}</Badge>
      </div>
      <p className="text-xs text-muted">{result.summary as string}</p>
      <RuleChecklist checks={result.checks as { rule: string; passed: boolean; reason: string | null }[]} />
    </div>
  );
}

function ReplacementSearchCard({ result }: { result: ToolResult }) {
  const eligible = (result.eligible_candidates as { employee_name: string; summary: string }[]) ?? [];
  const rejected = (result.rejected_candidates_shown as { employee_name: string; reason: string }[]) ?? [];
  return (
    <div className="space-y-3">
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
          Eligible ({result.eligible_count as number})
        </p>
        <div className="space-y-1">
          {eligible.map((c) => (
            <EmployeeChip key={c.employee_name} full_name={c.employee_name} />
          ))}
        </div>
      </div>
      {rejected.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Rejected (showing {rejected.length} of {result.rejected_count as number})
          </p>
          <ul className="space-y-1 text-xs text-muted">
            {rejected.map((c) => (
              <li key={c.employee_name}>
                <span className="font-medium text-foreground">{c.employee_name}</span> — {c.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SimulationCard({ result }: { result: ToolResult }) {
  const events = (result.events as { category: string; description: string; severity: string }[]) ?? [];
  const staffingImpacts =
    (result.staffing_impacts as {
      site_name: string;
      role_name: string;
      currently_assigned: number;
      minimum_required: number;
      status: string;
    }[]) ?? [];
  const eligible = (result.eligible_alternatives as { employee_name: string }[]) ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-md bg-gray-50 px-3 py-2 text-sm">
        <span className="text-muted">New planned end date:</span>
        <span className="font-medium text-foreground">{result.simulated_planned_end_date as string}</span>
        <span className="text-muted">(was {result.original_planned_end_date as string})</span>
        <span className="ml-auto">
          <SeverityBadge severity={result.overall_severity as string} />
        </span>
      </div>
      <ol className="space-y-2 border-l-2 border-border pl-4">
        {events.map((event, idx) => (
          <li key={idx}>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={event.severity} />
              <span className="font-mono text-[11px] text-muted">{event.category}</span>
            </div>
            <p className="text-sm text-foreground">{event.description}</p>
          </li>
        ))}
      </ol>
      {staffingImpacts.length > 0 && (
        <div className="space-y-1">
          {staffingImpacts.map((impact, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm">
              <span className="text-foreground">
                {impact.site_name} · {impact.role_name}
              </span>
              <span className="text-muted">
                {impact.currently_assigned} / {impact.minimum_required}
              </span>
              <StaffingStatusBadge status={impact.status} />
            </div>
          ))}
        </div>
      )}
      {eligible.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Eligible alternatives</p>
          <div className="space-y-1">
            {eligible.map((c) => (
              <EmployeeChip key={c.employee_name} full_name={c.employee_name} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StaffingStatusCard({ result }: { result: ToolResult }) {
  const coverage =
    (result.coverage as {
      site_name: string;
      role_name: string;
      currently_assigned: number;
      minimum_required: number;
      status: string;
    }[]) ?? [];
  return (
    <div className="space-y-1">
      {coverage.map((row, idx) => (
        <div key={idx} className="flex items-center gap-2 text-sm">
          <span className="text-foreground">
            {row.site_name} · {row.role_name}
          </span>
          <span className="text-muted">
            {row.currently_assigned} / {row.minimum_required}
          </span>
          <StaffingStatusBadge status={row.status} />
        </div>
      ))}
      {coverage.length === 0 && <p className="text-sm text-muted">No staffing shortages found.</p>}
    </div>
  );
}

function SearchResultsCard({ result }: { result: ToolResult }) {
  const employees =
    (result.employees as { id: number; full_name: string; role: string; site: string | null; availability_status: string }[]) ??
    [];
  return (
    <div className="space-y-1">
      {employees.map((e) => (
        <EmployeeChip key={e.id} full_name={e.full_name} role={e.role} site={e.site} />
      ))}
    </div>
  );
}

function ReliefDueCard({ result }: { result: ToolResult }) {
  const items =
    (result.items as { employee_name: string; site_name: string; days_remaining: number; risk: string }[]) ?? [];
  return (
    <div className="space-y-1">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center gap-2 text-sm">
          <span className="font-medium text-foreground">{item.employee_name}</span>
          <span className="text-muted">
            {item.site_name} · {item.days_remaining} day(s)
          </span>
          <Badge tone={item.risk === "no_reliever" ? "critical" : "neutral"}>{item.risk.replace("_", " ")}</Badge>
        </div>
      ))}
      {items.length === 0 && <p className="text-sm text-muted">Nobody needs relief in this window.</p>}
    </div>
  );
}

const RENDERERS: Record<string, (props: { result: ToolResult }) => React.JSX.Element> = {
  search_employees: SearchResultsCard,
  get_relief_due: ReliefDueCard,
  evaluate_replacement: EligibilityCard,
  find_replacement_candidates: ReplacementSearchCard,
  simulate_extension: SimulationCard,
  get_staffing_status: StaffingStatusCard,
};

export function AssistantToolResultCard({ tool, result }: { tool: string; result: ToolResult }) {
  const status = result.status as string;
  if (status === "ambiguous") return <AmbiguousNotice result={result} />;
  if (status === "not_found" || status === "error") return <NotFoundOrErrorNotice result={result} />;

  const Renderer = RENDERERS[tool];
  if (!Renderer) return null;
  return <Renderer result={result} />;
}
