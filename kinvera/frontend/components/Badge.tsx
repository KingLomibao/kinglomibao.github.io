// A small status pill. `tone` maps to a fixed set of semantic colors
// so the same status always looks the same everywhere in the app.

const TONE_CLASSES: Record<string, string> = {
  neutral: "bg-gray-100 text-gray-700",
  positive: "bg-emerald-100 text-emerald-800",
  caution: "bg-amber-100 text-amber-800",
  critical: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
};

export type BadgeTone = keyof typeof TONE_CLASSES;

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: BadgeTone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}

const AVAILABILITY_TONE: Record<string, BadgeTone> = {
  assigned: "info",
  available: "positive",
  on_leave: "caution",
  unavailable: "critical",
};

export function AvailabilityBadge({ status }: { status: string }) {
  return <Badge tone={AVAILABILITY_TONE[status] ?? "neutral"}>{status.replace("_", " ")}</Badge>;
}

const QUALIFICATION_TONE: Record<string, BadgeTone> = {
  valid: "positive",
  expiring_soon: "caution",
  expired: "critical",
};

export function QualificationStatusBadge({ status }: { status: string }) {
  return <Badge tone={QUALIFICATION_TONE[status] ?? "neutral"}>{status.replace("_", " ")}</Badge>;
}

const SEVERITY_TONE: Record<string, BadgeTone> = {
  info: "neutral",
  low: "info",
  medium: "caution",
  high: "critical",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return <Badge tone={SEVERITY_TONE[severity] ?? "neutral"}>{severity}</Badge>;
}

const ASSIGNMENT_STATUS_TONE: Record<string, BadgeTone> = {
  active: "info",
  planned: "neutral",
  completed: "positive",
  cancelled: "critical",
};

export function AssignmentStatusBadge({ status }: { status: string }) {
  return <Badge tone={ASSIGNMENT_STATUS_TONE[status] ?? "neutral"}>{status}</Badge>;
}

const STAFFING_TONE: Record<string, BadgeTone> = {
  meeting: "positive",
  short: "critical",
};

export function StaffingStatusBadge({ status }: { status: string }) {
  return <Badge tone={STAFFING_TONE[status] ?? "neutral"}>{status === "short" ? "short-staffed" : "meeting minimum"}</Badge>;
}
