"use client";

import { useState } from "react";
import { simulateExtension } from "@/lib/api";
import type { ExtensionSimulationResponse } from "@/lib/types";
import { Card } from "@/components/Card";
import { SeverityBadge, StaffingStatusBadge } from "@/components/Badge";
import { EligibilityList } from "@/components/EligibilityList";
import { LoadingState } from "@/components/RequestState";

/**
 * The "what happens if this assignment runs N days longer?" scenario
 * tool. This is a deterministic operational-impact preview, not an AI
 * prediction: every number and event it shows comes straight from the
 * backend's simulate-extension endpoint, which never writes to the
 * database (see `is_destructive` in the response, always false here).
 */
export function SimulationPanel({ assignmentId, employeeName }: { assignmentId: number; employeeName: string }) {
  const [extensionDays, setExtensionDays] = useState(14);
  const [result, setResult] = useState<ExtensionSimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await simulateExtension(assignmentId, extensionDays);
      setResult(response);
    } catch (err) {
      setError(String((err as Error).message ?? err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Assignment Extension - Scenario Simulation">
      <p className="mb-4 text-xs text-muted">
        Deterministic operational impact analysis. This does not modify {employeeName}&apos;s assignment or any other
        record - it previews what the downstream effect would be.
      </p>
      <div className="mb-4 flex items-end gap-3">
        <label className="flex flex-col text-xs font-medium text-muted">
          Extension (days)
          <input
            type="number"
            min={1}
            max={180}
            value={extensionDays}
            onChange={(e) => setExtensionDays(Number(e.target.value))}
            className="mt-1 w-28 rounded-md border border-border px-2 py-1.5 text-sm outline-none focus:border-accent"
          />
        </label>
        <button
          type="button"
          onClick={runSimulation}
          disabled={loading}
          className="rounded-md bg-accent px-4 py-1.5 text-sm font-medium text-accent-foreground disabled:opacity-60"
        >
          {loading ? "Running..." : "Run Simulation"}
        </button>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}
      {loading && <LoadingState label="Calculating downstream impact..." />}

      {result && !loading && (
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-3 rounded-md bg-gray-50 px-4 py-3 text-sm">
            <span className="text-muted">New planned end date:</span>
            <span className="font-medium text-foreground">{result.simulated_planned_end_date}</span>
            <span className="text-muted">(was {result.original_planned_end_date})</span>
            <span className="ml-auto">
              <SeverityBadge severity={result.overall_severity} />
            </span>
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Downstream Impact</h3>
            <ol className="flex flex-col gap-2 border-l-2 border-border pl-4">
              {result.events.map((event, idx) => (
                <li key={idx} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-border" />
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={event.severity} />
                    <span className="text-xs font-mono text-muted">{event.category}</span>
                  </div>
                  <p className="mt-0.5 text-sm text-foreground">{event.description}</p>
                </li>
              ))}
            </ol>
          </div>

          {result.staffing_impacts.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Staffing Impact</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted">
                    <th className="pb-1 font-medium">Site</th>
                    <th className="pb-1 font-medium">Role</th>
                    <th className="pb-1 font-medium">Coverage / Min</th>
                    <th className="pb-1 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.staffing_impacts.map((impact) => (
                    <tr key={`${impact.site_id}-${impact.role_id}`} className="border-t border-border">
                      <td className="py-1.5 text-foreground">{impact.site_name}</td>
                      <td className="py-1.5 text-muted">{impact.role_name}</td>
                      <td className="py-1.5 text-muted">
                        {impact.currently_assigned} / {impact.minimum_required}
                      </td>
                      <td className="py-1.5">
                        <StaffingStatusBadge status={impact.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(result.eligible_alternatives.length > 0 || result.rejected_alternatives.length > 0) && (
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Alternative Coverage</h3>
              <EligibilityList eligible={result.eligible_alternatives} rejected={result.rejected_alternatives} />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
