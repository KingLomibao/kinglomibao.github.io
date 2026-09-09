"use client";

import { useEffect, useState } from "react";
import { listEmployees } from "@/lib/api";
import type { EmployeeSummary } from "@/lib/types";
import { Card } from "@/components/Card";
import { SimulationPanel } from "@/components/SimulationPanel";
import { ReplacementSearchPanel } from "@/components/ReplacementSearchPanel";
import { EmptyState, ErrorState } from "@/components/RequestState";

export default function ScenarioSimulationPage() {
  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<EmployeeSummary[]>([]);
  const [selected, setSelected] = useState<EmployeeSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!search) {
      return;
    }
    const handle = setTimeout(() => {
      listEmployees({ search })
        .then((results) => setMatches(results.filter((e) => e.current_assignment)))
        .catch((err) => setError(String(err.message ?? err)));
    }, 200);
    return () => clearTimeout(handle);
  }, [search]);

  const visibleMatches = search ? matches : [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Scenario Simulation</h1>
        <p className="text-sm text-muted">
          Select a currently assigned employee to preview the downstream, deterministic impact of extending their
          assignment. This tool never modifies live assignment records.
        </p>
      </div>

      <Card title="Select Employee">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSelected(null);
          }}
          placeholder="Search a currently assigned employee, e.g. John Smith..."
          className="w-full max-w-md rounded-md border border-border px-3 py-1.5 text-sm outline-none focus:border-accent"
        />
        {error && <ErrorState message={error} />}
        {search && !selected && (
          <ul className="mt-3 divide-y divide-border">
            {visibleMatches.length === 0 && <EmptyState message="No currently assigned employee matches." />}
            {visibleMatches.map((employee) => (
              <li key={employee.id}>
                <button
                  type="button"
                  onClick={() => setSelected(employee)}
                  className="w-full py-2 text-left text-sm hover:text-accent"
                >
                  <span className="font-medium text-foreground">{employee.full_name}</span>
                  <span className="ml-2 text-muted">
                    {employee.role.name} · {employee.current_assignment?.site_name}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {selected?.current_assignment && (
        <>
          <ReplacementSearchPanel assignmentId={selected.current_assignment.id} />
          <SimulationPanel assignmentId={selected.current_assignment.id} employeeName={selected.full_name} />
        </>
      )}
    </div>
  );
}
