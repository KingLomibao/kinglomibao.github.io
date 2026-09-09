// A thin wrapper around fetch for talking to the OpsPilot API.
//
// Every function here maps 1:1 to a FastAPI route - this file has no
// opinions about *when* to call the API (that's each page's job), it
// just knows *how*.

import type {
  DashboardSummary,
  EmployeeDetail,
  EmployeeSummary,
  ExtensionSimulationResponse,
  QualificationRisk,
  ReliefDueItem,
  ReplacementSearchResponse,
  Site,
  StaffingCoverage,
  WorkforceMovement,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const getDashboardSummary = () => apiFetch<DashboardSummary>("/api/dashboard/summary");

export const listEmployees = (params?: { search?: string; roleId?: number; availabilityStatus?: string }) => {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.roleId) query.set("role_id", String(params.roleId));
  if (params?.availabilityStatus) query.set("availability_status", params.availabilityStatus);
  const qs = query.toString();
  return apiFetch<EmployeeSummary[]>(`/api/employees${qs ? `?${qs}` : ""}`);
};

export const getEmployee = (employeeId: number) => apiFetch<EmployeeDetail>(`/api/employees/${employeeId}`);

export const listSites = () => apiFetch<Site[]>("/api/sites");

export const listStaffingCoverage = () => apiFetch<StaffingCoverage[]>("/api/staffing/coverage");

export const listStaffingShortages = () => apiFetch<StaffingCoverage[]>("/api/staffing/shortages");

export const listQualificationRisks = () => apiFetch<QualificationRisk[]>("/api/qualifications/risks");

export const listReliefDue = (windowDays?: number) =>
  apiFetch<ReliefDueItem[]>(`/api/relief/due${windowDays ? `?window_days=${windowDays}` : ""}`);

export const listUpcomingMovements = (windowDays = 30) =>
  apiFetch<WorkforceMovement[]>(`/api/movements/upcoming?window_days=${windowDays}`);

export const getReplacementCandidates = (assignmentId: number) =>
  apiFetch<ReplacementSearchResponse>(`/api/assignments/${assignmentId}/replacement-candidates`);

export const simulateExtension = (assignmentId: number, extensionDays: number) =>
  apiFetch<ExtensionSimulationResponse>(`/api/assignments/${assignmentId}/simulate-extension`, {
    method: "POST",
    body: JSON.stringify({ extension_days: extensionDays }),
  });
