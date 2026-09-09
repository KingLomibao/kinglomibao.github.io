"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getDashboardSummary,
  listQualificationRisks,
  listReliefDue,
  listStaffingCoverage,
  listUpcomingMovements,
} from "@/lib/api";
import type {
  DashboardSummary,
  QualificationRisk,
  ReliefDueItem,
  StaffingCoverage,
  WorkforceMovement,
} from "@/lib/types";
import { Card, KpiCard } from "@/components/Card";
import { ErrorState, LoadingState, EmptyState } from "@/components/RequestState";
import { QualificationStatusBadge, StaffingStatusBadge } from "@/components/Badge";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [reliefDue, setReliefDue] = useState<ReliefDueItem[] | null>(null);
  const [coverage, setCoverage] = useState<StaffingCoverage[] | null>(null);
  const [qualRisks, setQualRisks] = useState<QualificationRisk[] | null>(null);
  const [movements, setMovements] = useState<WorkforceMovement[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getDashboardSummary(),
      listReliefDue(30),
      listStaffingCoverage(),
      listQualificationRisks(),
      listUpcomingMovements(30),
    ])
      .then(([s, r, c, q, m]) => {
        setSummary(s);
        setReliefDue(r);
        setCoverage(c);
        setQualRisks(q);
        setMovements(m);
      })
      .catch((err) => setError(String(err.message ?? err)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!summary) return <LoadingState />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Workforce Overview</h1>
        <p className="text-sm text-muted">A live read of Ironbridge Field Operations&apos; current deployment.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard label="Active Workforce" value={summary.total_active_workforce} />
        <KpiCard label="Currently Assigned" value={summary.currently_assigned} />
        <KpiCard label="Available" value={summary.available} />
        <KpiCard label="On Leave" value={summary.on_leave} />
        <KpiCard label="Unavailable" value={summary.unavailable} />
        <KpiCard
          label={`Relief Due (${summary.relief_window_days}d)`}
          value={summary.relief_due_in_window}
          hint="active assignments ending soon"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
        <KpiCard
          label="Qualification Risks"
          value={summary.qualification_risks}
          hint="expired or expiring within 30 days"
        />
        <KpiCard label="Staffing Shortages" value={summary.staffing_shortages} hint="site + role below minimum" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Upcoming Relief" action={<Link href="/employees" className="text-xs font-medium text-accent">View employees →</Link>}>
          {reliefDue && reliefDue.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="pb-2 font-medium">Employee</th>
                  <th className="pb-2 font-medium">Site</th>
                  <th className="pb-2 font-medium">Ends in</th>
                  <th className="pb-2 font-medium">Reliever</th>
                </tr>
              </thead>
              <tbody>
                {reliefDue.slice(0, 8).map((item) => (
                  <tr key={item.assignment_id} className="border-t border-border">
                    <td className="py-2">
                      <Link href={`/employees/${item.employee_id}`} className="font-medium text-foreground hover:text-accent">
                        {item.employee_name}
                      </Link>
                      <div className="text-xs text-muted">{item.role_name}</div>
                    </td>
                    <td className="py-2 text-muted">{item.site_name}</td>
                    <td className="py-2 text-muted">
                      {item.days_remaining >= 0 ? `${item.days_remaining} day(s)` : "overdue"}
                    </td>
                    <td className="py-2">
                      {item.reliever_status === "planned" ? (
                        <span className="text-foreground">{item.reliever_employee_name}</span>
                      ) : (
                        <span className="text-red-700">none planned</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState message="No assignments need relief in this window." />
          )}
        </Card>

        <Card title="Staffing Coverage">
          {coverage && coverage.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="pb-2 font-medium">Site</th>
                  <th className="pb-2 font-medium">Role</th>
                  <th className="pb-2 font-medium">Assigned / Min</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {coverage
                  .slice()
                  .sort((a, b) => b.shortage - a.shortage)
                  .slice(0, 8)
                  .map((item) => (
                    <tr key={`${item.site_id}-${item.role_id}`} className="border-t border-border">
                      <td className="py-2 font-medium text-foreground">{item.site_name}</td>
                      <td className="py-2 text-muted">{item.role_name}</td>
                      <td className="py-2 text-muted">
                        {item.currently_assigned} / {item.minimum_required}
                      </td>
                      <td className="py-2">
                        <StaffingStatusBadge status={item.status} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ) : (
            <EmptyState message="No staffing requirements defined." />
          )}
        </Card>

        <Card title="Qualification Risks">
          {qualRisks && qualRisks.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="pb-2 font-medium">Employee</th>
                  <th className="pb-2 font-medium">Qualification</th>
                  <th className="pb-2 font-medium">Expires</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {qualRisks.slice(0, 8).map((risk) => (
                  <tr key={`${risk.employee_id}-${risk.qualification_id}`} className="border-t border-border">
                    <td className="py-2">
                      <Link href={`/employees/${risk.employee_id}`} className="font-medium text-foreground hover:text-accent">
                        {risk.employee_name}
                      </Link>
                    </td>
                    <td className="py-2 text-muted">{risk.qualification_name}</td>
                    <td className="py-2 text-muted">{risk.expiry_date}</td>
                    <td className="py-2">
                      <QualificationStatusBadge status={risk.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState message="No qualification risks in the near term." />
          )}
        </Card>

        <Card title="Upcoming Movements">
          {movements && movements.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Employee</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Site</th>
                </tr>
              </thead>
              <tbody>
                {movements.slice(0, 8).map((movement) => (
                  <tr key={movement.id} className="border-t border-border">
                    <td className="py-2 text-muted">{movement.movement_date}</td>
                    <td className="py-2">
                      <Link href={`/employees/${movement.employee_id}`} className="font-medium text-foreground hover:text-accent">
                        {movement.employee_name}
                      </Link>
                    </td>
                    <td className="py-2 text-muted">{movement.movement_type.replace("_", " ")}</td>
                    <td className="py-2 text-muted">{movement.to_site_name ?? movement.from_site_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState message="No movements scheduled in this window." />
          )}
        </Card>
      </div>
    </div>
  );
}
