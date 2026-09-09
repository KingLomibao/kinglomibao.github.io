// TypeScript mirrors of the FastAPI response schemas
// (backend/app/schemas/*.py). Keeping these in one file makes it easy
// to see, at a glance, exactly what shape of data the UI expects from
// the API.

export interface Role {
  id: number;
  code: string;
  name: string;
  category: string;
}

export interface Site {
  id: number;
  code: string;
  name: string;
  location: string;
  status: string;
}

export interface Assignment {
  id: number;
  employee_id: number;
  employee_name: string;
  site_id: number;
  site_name: string;
  role_id: number;
  role_name: string;
  start_date: string;
  planned_end_date: string;
  actual_end_date: string | null;
  status: string;
  relieving_assignment_id: number | null;
  notes: string | null;
}

export interface Qualification {
  id: number;
  code: string;
  name: string;
  description: string | null;
}

export interface EmployeeQualification {
  id: number;
  qualification: Qualification;
  issue_date: string;
  expiry_date: string;
  status: "valid" | "expiring_soon" | "expired";
}

export interface EmployeeSummary {
  id: number;
  employee_number: string;
  full_name: string;
  role: Role;
  employment_status: string;
  availability_status: string;
  home_location: string | null;
  active: boolean;
  current_assignment: Assignment | null;
}

export interface EmployeeDetail extends EmployeeSummary {
  hire_date: string;
  next_assignment: Assignment | null;
  qualifications: EmployeeQualification[];
  assignment_history: Assignment[];
}

export interface ReliefDueItem {
  assignment_id: number;
  employee_id: number;
  employee_name: string;
  role_id: number;
  role_name: string;
  site_id: number;
  site_name: string;
  planned_end_date: string;
  days_remaining: number;
  reliever_employee_id: number | null;
  reliever_employee_name: string | null;
  reliever_assignment_id: number | null;
  reliever_status: "planned" | "none";
  risk: "no_reliever" | "reliever_planned" | "overdue";
}

export interface StaffingCoverage {
  site_id: number;
  site_name: string;
  role_id: number;
  role_name: string;
  minimum_required: number;
  currently_assigned: number;
  shortage: number;
  status: "meeting" | "short";
}

export interface QualificationRisk {
  employee_id: number;
  employee_name: string;
  qualification_id: number;
  qualification_name: string;
  expiry_date: string;
  status: "valid" | "expiring_soon" | "expired";
}

export interface WorkforceMovement {
  id: number;
  employee_id: number;
  employee_name: string;
  movement_type: string;
  movement_date: string;
  from_site_id: number | null;
  from_site_name: string | null;
  to_site_id: number | null;
  to_site_name: string | null;
  notes: string | null;
}

export interface DashboardSummary {
  total_active_workforce: number;
  currently_assigned: number;
  available: number;
  on_leave: number;
  unavailable: number;
  relief_due_in_window: number;
  relief_window_days: number;
  qualification_risks: number;
  staffing_shortages: number;
  total_sites: number;
}

export interface RuleCheck {
  rule: string;
  passed: boolean;
  reason: string | null;
}

export interface EligibilityResult {
  employee_id: number;
  employee_name: string;
  role_id: number;
  site_id: number;
  window_start: string;
  window_end: string;
  eligible: boolean;
  checks: RuleCheck[];
  summary: string;
}

export interface ReplacementSearchResponse {
  target_assignment_id: number;
  target_employee_id: number;
  target_employee_name: string;
  role_id: number;
  role_name: string;
  site_id: number;
  site_name: string;
  window_start: string;
  window_end: string;
  eligible_candidates: EligibilityResult[];
  rejected_candidates: EligibilityResult[];
}

export interface ImpactEvent {
  category: string;
  description: string;
  severity: "info" | "low" | "medium" | "high";
  employee_id: number | null;
  assignment_id: number | null;
  site_id: number | null;
}

export interface ExtensionSimulationResponse {
  assignment_id: number;
  employee_id: number;
  employee_name: string;
  extension_days: number;
  original_planned_end_date: string;
  simulated_planned_end_date: string;
  is_destructive: boolean;
  overall_severity: "info" | "low" | "medium" | "high";
  events: ImpactEvent[];
  staffing_impacts: StaffingCoverage[];
  eligible_alternatives: EligibilityResult[];
  rejected_alternatives: EligibilityResult[];
}

// --- AI Assistant (Phase 2) -------------------------------------------
//
// `tool_results` carries the raw, deterministic data each Kinvera tool
// returned - this is the ground truth the UI renders structured
// widgets from. `answer` is the LLM's explanation of that data; it is
// display-only prose, never a second source of operational fact.

export interface AssistantToolCall {
  tool: string;
  arguments: Record<string, unknown>;
}

export interface AssistantToolResult {
  tool: string;
  result: Record<string, unknown>;
}

export interface AssistantChatResponse {
  answer: string;
  tool_calls: AssistantToolCall[];
  sources: string[];
  tool_results: AssistantToolResult[];
}
