"use client";

import { useEffect, useState } from "react";
import { getReplacementCandidates } from "@/lib/api";
import type { ReplacementSearchResponse } from "@/lib/types";
import { Card } from "@/components/Card";
import { EligibilityList } from "@/components/EligibilityList";
import { LoadingState, ErrorState } from "@/components/RequestState";

export function ReplacementSearchPanel({ assignmentId }: { assignmentId: number }) {
  const [result, setResult] = useState<ReplacementSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReplacementCandidates(assignmentId)
      .then(setResult)
      .catch((err) => setError(String(err.message ?? err)));
  }, [assignmentId]);

  return (
    <Card title={`Who Can Replace ${result?.target_employee_name ?? "This Employee"}?`}>
      <p className="mb-4 text-xs text-muted">
        Deterministic eligibility results for the window {result?.window_start} to {result?.window_end}, evaluated
        against role, availability, qualification validity, and scheduling rules.
      </p>
      {error && <ErrorState message={error} />}
      {!error && !result && <LoadingState />}
      {result && <EligibilityList eligible={result.eligible_candidates} rejected={result.rejected_candidates} />}
    </Card>
  );
}
