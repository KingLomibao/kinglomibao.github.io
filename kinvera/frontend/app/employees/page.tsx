"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listEmployees } from "@/lib/api";
import type { EmployeeSummary } from "@/lib/types";
import { Card } from "@/components/Card";
import { AvailabilityBadge } from "@/components/Badge";
import { ErrorState, LoadingState, EmptyState } from "@/components/RequestState";

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<EmployeeSummary[] | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      listEmployees({ search: search || undefined })
        .then(setEmployees)
        .catch((err) => setError(String(err.message ?? err)));
    }, 200);
    return () => clearTimeout(handle);
  }, [search]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Employees</h1>
          <p className="text-sm text-muted">Search the full Ironbridge workforce roster.</p>
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name..."
          className="w-64 rounded-md border border-border bg-surface px-3 py-1.5 text-sm outline-none focus:border-accent"
        />
      </div>

      <Card>
        {error && <ErrorState message={error} />}
        {!error && !employees && <LoadingState />}
        {!error && employees && employees.length === 0 && <EmptyState message="No employees match this search." />}
        {!error && employees && employees.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="pb-2 font-medium">Employee</th>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Current Site</th>
                <th className="pb-2 font-medium">Home Location</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((employee) => (
                <tr key={employee.id} className="border-t border-border">
                  <td className="py-2">
                    <Link href={`/employees/${employee.id}`} className="font-medium text-foreground hover:text-accent">
                      {employee.full_name}
                    </Link>
                    <div className="text-xs text-muted">{employee.employee_number}</div>
                  </td>
                  <td className="py-2 text-muted">{employee.role.name}</td>
                  <td className="py-2">
                    <AvailabilityBadge status={employee.availability_status} />
                  </td>
                  <td className="py-2 text-muted">{employee.current_assignment?.site_name ?? "—"}</td>
                  <td className="py-2 text-muted">{employee.home_location ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
