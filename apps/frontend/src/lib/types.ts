/** Shared API shapes. Replaces the `any` that used to flow through every view. */

export interface Session {
  user_id: string;
  email: string;
  full_name: string;
  token: string;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  description: string;
  location: string;
  location_type: string;
  is_remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  currency: string;
  apply_url: string;
  source: string;
  created_at: string | null;
}

/** A posting from an external board, which has no local id or schema. */
export interface ExternalJob {
  id?: string;
  title?: string;
  position?: string;
  name?: string;
  company?: string;
  company_name?: string;
  location?: string;
  description?: string;
  url?: string;
  apply_url?: string;
  is_remote?: boolean;
}

export interface JobSearchResponse<T> {
  results: T[];
  source?: string;
  /** False when the board itself failed, as opposed to matching nothing. */
  available?: boolean;
}

export interface SemanticHit {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  apply_url: string;
  score: number;
  match: string;
}

export type ApplicationStatus =
  | "applied"
  | "under_review"
  | "technical_test"
  | "hr_interview"
  | "technical_interview"
  | "offer"
  | "rejected";

export interface Application {
  id: string;
  job_id: string;
  resume_id: string;
  job_title: string;
  company: string;
  status: ApplicationStatus;
  cover_letter: string;
  source_platform: string | null;
  applied_at: string | null;
  created_at: string;
}

export interface ApplicationStats {
  total: number;
  by_status: Record<string, number>;
}

export interface Resume {
  id: string;
  title: string;
  file_url: string;
  content_preview: string;
  ats_score: number | null;
  ats_breakdown: AtsBreakdown | Record<string, never>;
  created_at: string | null;
}

export interface AtsBreakdown {
  matched_skills?: string[];
  missing_skills?: string[];
  suggestions?: string[];
  strengths?: string[];
}

export interface CalendarEvent {
  id: string;
  title: string;
  event_type: "interview" | "deadline" | "reminder" | string;
  date: string | null;
  notes: string;
  location: string;
  status: "scheduled" | "completed" | "cancelled" | string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  channel: string;
  status: string;
  created_at: string;
}

export interface Analytics {
  total_applications: number;
  interview_rate: number;
  offer_rate: number;
  rejection_rate: number;
  response_rate: number;
  interviews: number;
  offers: number;
  rejected: number;
  avg_ats_score: number | null;
  top_companies: { name: string; count: number }[];
  applications_over_time: { date: string; count: number }[];
  top_skills: { name: string; count: number }[];
}

export interface LlmConfig {
  id: string;
  provider_name: string;
  has_key: boolean;
  base_url: string;
  model: string;
  is_active: boolean;
}

export interface MatchResult {
  compatibility_score: number;
  match_reasons: { text: string; type: "match" | "gap" }[];
  suggestions: string[];
  provider?: string;
}

export interface AtsResult {
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  suggestions: string[];
  strengths: string[];
  provider?: string;
}

export interface CoverLetter {
  id: string;
  title: string;
  content: string;
  language: string;
  tone: string;
  created_at: string;
}

export interface GithubImport {
  profile: { name?: string; bio?: string; avatar_url?: string; login?: string };
  repos: { name: string; description?: string; language?: string; stars?: number }[];
  skills: string[];
  total_repos: number;
}

/** Profile positioning derived from the user's own resume. */
export interface ProfileSuggestion {
  headline?: string;
  about?: string;
  skills?: string[];
  suggested_roles?: string[];
  experience_years?: number;
  gaps?: string[];
  analysis?: string;
  url?: string;
}
