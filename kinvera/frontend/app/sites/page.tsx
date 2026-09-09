"use client";

import { useEffect, useState } from "react";
import { listSites, listStaffingCoverage } from "@/lib/api";
import type { Site, StaffingCoverage } from "@/lib/types";
import { Card } from "@/components/Card";
import { Badge, StaffingStatusBadge } from "@/components/Badge";
import { ErrorState, LoadingState } from "@/components/RequestState";

export default function SitesPage() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [coverage, setCoverage] = useState<StaffingCoverage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listSites(), listStaffingCoverage()])
      .then(([s, c]) => {
        setSites(s);
        setCoverage(c);
      })
      .catch((err) => setError(String(err.message ?? err)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!sites || !coverage) return <LoadingState />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Sites &amp; Projects</h1>
        <p className="text-sm text-muted">Operational sites and their staffing coverage against defined minimums.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {sites.map((site) => {
          const siteCoverage = coverage.filter((c) => c.site_id === site.id);
          return (
            <Card key={site.id} title={site.name}>
              <div className="mb-3 flex items-center justify-between text-xs text-muted">
                <span>{site.location}</span>
                <Badge tone={site.status === "active" ? "positive" : site.status === "demobilizing" ? "caution" : "neutral"}>
                  {site.status}
                </Badge>
              </div>
              {siteCoverage.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-muted">
                      <th className="pb-2 font-medium">Role</th>
                      <th className="pb-2 font-medium">Assigned / Min</th>
                      <th className="pb-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {siteCoverage.map((c) => (
                      <tr key={c.role_id} className="border-t border-border">
                        <td className="py-1.5 text-foreground">{c.role_name}</td>
                        <td className="py-1.5 text-muted">
                          {c.currently_assigned} / {c.minimum_required}
                        </td>
                        <td className="py-1.5">
                          <StaffingStatusBadge status={c.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-muted">No staffing minimums defined for this site.</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
