"use client";

import { use, useEffect, useState } from "react";
import { getEmployee } from "@/lib/api";
import type { EmployeeDetail } from "@/lib/types";
import { Card } from "@/components/Card";
import { AvailabilityBadge, AssignmentStatusBadge, QualificationStatusBadge } from "@/components/Badge";
import { ErrorState, LoadingState, EmptyState } from "@/components/RequestState";
import { SimulationPanel } from "@/components/SimulationPanel";
import { ReplacementSearchPanel } from "@/components/ReplacementSearchPanel";

export default function EmployeeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const employeeId = Number(id);
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEmployee(employeeId)
      .then(setEmployee)
      .catch((err) => setError(String(err.message ?? err)));
  }, [employeeId]);

  if (error) return <ErrorState message={error} />;
  if (!employee) return <LoadingState />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">{employee.full_name}</h1>
          <p className="text-sm text-muted">
            {employee.employee_number} · {employee.role.name}
          </p>
        </div>
        <AvailabilityBadge status={employee.availability_status} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Current Assignment">
          {employee.current_assignment ? (
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-muted">Site</dt>
              <dd className="text-foreground">{employee.current_assignment.site_name}</dd>
              <dt className="text-muted">Start</dt>
              <dd className="text-foreground">{employee.current_assignment.start_date}</dd>
              <dt className="text-muted">Planned end</dt>
              <dd className="text-foreground">{employee.current_assignment.planned_end_date}</dd>
              <dt className="text-muted">Status</dt>
              <dd>
                <AssignmentStatusBadge status={employee.current_assignment.status} />
              </dd>
            </dl>
          ) : (
            <EmptyState message="Not currently assigned to a site." />
          )}
        </Card>

        <Card title="Next Planned Assignment">
          {employee.next_assignment ? (
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-muted">Site</dt>
              <dd className="text-foreground">{employee.next_assignment.site_name}</dd>
              <dt className="text-muted">Start</dt>
              <dd className="text-foreground">{employee.next_assignment.start_date}</dd>
              <dt className="text-muted">Planned end</dt>
              <dd className="text-foreground">{employee.next_assignment.planned_end_date}</dd>
              {employee.next_assignment.relieving_assignment_id && (
                <>
                  <dt className="text-muted">Relieving</dt>
                  <dd className="text-foreground">assignment #{employee.next_assignment.relieving_assignment_id}</dd>
                </>
              )}
            </dl>
          ) : (
            <EmptyState message="No planned future assignment." />
          )}
        </Card>
      </div>

      <Card title="Qualifications">
        {employee.qualifications.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="pb-2 font-medium">Qualification</th>
                <th className="pb-2 font-medium">Issued</th>
                <th className="pb-2 font-medium">Expires</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {employee.qualifications.map((eq) => (
                <tr key={eq.id} className="border-t border-border">
                  <td className="py-2 text-foreground">{eq.qualification.name}</td>
                  <td className="py-2 text-muted">{eq.issue_date}</td>
                  <td className="py-2 text-muted">{eq.expiry_date}</td>
                  <td className="py-2">
                    <QualificationStatusBadge status={eq.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState message="No qualifications on file." />
        )}
      </Card>

      {employee.assignment_history.length > 0 && (
        <Card title="Recent Assignment History">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="pb-2 font-medium">Site</th>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Start</th>
                <th className="pb-2 font-medium">Ended</th>
              </tr>
            </thead>
            <tbody>
              {employee.assignment_history.map((a) => (
                <tr key={a.id} className="border-t border-border">
                  <td className="py-2 text-foreground">{a.site_name}</td>
                  <td className="py-2 text-muted">{a.role_name}</td>
                  <td className="py-2 text-muted">{a.start_date}</td>
                  <td className="py-2 text-muted">{a.actual_end_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {employee.current_assignment && (
        <>
          <ReplacementSearchPanel assignmentId={employee.current_assignment.id} />
          <SimulationPanel assignmentId={employee.current_assignment.id} employeeName={employee.full_name} />
        </>
      )}
    </div>
  );
}
