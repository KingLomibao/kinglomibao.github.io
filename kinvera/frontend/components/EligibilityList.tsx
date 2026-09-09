"use client";

import { useState } from "react";
import type { EligibilityResult } from "@/lib/types";
import { Badge } from "@/components/Badge";

function CandidateRow({ candidate }: { candidate: EligibilityResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="border-t border-border py-2 first:border-t-0">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start justify-between gap-4 text-left"
      >
        <div>
          <p className="text-sm font-medium text-foreground">{candidate.employee_name}</p>
          <p className="text-xs text-muted">{candidate.summary}</p>
        </div>
        <Badge tone={candidate.eligible ? "positive" : "critical"}>{candidate.eligible ? "eligible" : "not eligible"}</Badge>
      </button>
      {expanded && (
        <ul className="mt-2 space-y-1 rounded-md bg-gray-50 p-3 text-xs">
          {candidate.checks.map((check) => (
            <li key={check.rule} className="flex items-start gap-2">
              <span className={check.passed ? "text-emerald-700" : "text-red-700"}>{check.passed ? "✓" : "✗"}</span>
              <span className="text-muted">
                <span className="font-mono text-[11px] text-foreground">{check.rule}</span>
                {check.reason && <> — {check.reason}</>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function EligibilityList({
  eligible,
  rejected,
}: {
  eligible: EligibilityResult[];
  rejected: EligibilityResult[];
}) {
  const [showRejected, setShowRejected] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
          Eligible ({eligible.length})
        </h3>
        {eligible.length === 0 ? (
          <p className="text-sm text-muted">No eligible candidates found.</p>
        ) : (
          <ul>
            {eligible.map((c) => (
              <CandidateRow key={c.employee_id} candidate={c} />
            ))}
          </ul>
        )}
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowRejected((v) => !v)}
          className="text-xs font-semibold uppercase tracking-wide text-muted hover:text-accent"
        >
          {showRejected ? "Hide" : "Show"} rejected candidates ({rejected.length})
        </button>
        {showRejected && (
          <ul className="mt-2">
            {rejected.map((c) => (
              <CandidateRow key={c.employee_id} candidate={c} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
