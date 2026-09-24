export type Role = 'student' | 'employer' | 'admin';
export type User = {
  id: number;
  name: string;
  email: string;
  role: Role;
  email_matches: boolean;
  email_applications: boolean;
};
export type Project = { title: string; description: string; technologies: string[] };
export type Profile = {
  id: number;
  extracted_skills: string[];
  coursework: string[];
  projects: Project[];
  degree: string;
  location: string;
  preferences: { work_mode?: string; interests?: string };
  version: number;
};
export type Company = {
  verification_status: string;
  reviewed_at: string | null;
  demo_company: boolean;
  company_name: string;
  website: string;
  industry: string;
  location: string;
  description: string;
};
export type Listing = {
  employer_id: number;
  admin_hidden: boolean;
  id: number;
  title: string;
  description: string;
  required_skills: string[];
  location: string;
  work_mode: string;
  duration: string;
  stipend_min: string | null;
  stipend_max: string | null;
  currency: string | null;
  deadline: string | null;
  status: string;
  content_version: number;
  company: Company;
  moderation?: {
    manual_review?: { decision: string; at: string; reason: string };
    classification?: string;
    risk_reasons?: string[];
    suggested_changes?: string[];
    error?: string;
  };
  moderation_model?: string;
  provenance: { kind?: string };
  created_at: string;
};
export type Match = {
  internship: Listing;
  similarity: number;
  percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string;
  score_help: string;
};
export type Feedback = {
  summary: string;
  strengths: string[];
  potential_gaps: string[];
  next_steps: string[];
  practice_questions: string[];
};
export type Notice = {
  id: number;
  title: string;
  body: string;
  type: string;
  read_at: string | null;
  feedback: Feedback | null;
  feedback_state: string;
  related: { application_id?: number; internship_id?: number };
  created_at: string;
  email_state?: string;
};
export type Application = {
  id: number;
  internship_id: number;
  internship_title: string;
  student_name: string;
  status: string;
  cover_message: string;
  profile_snapshot: Partial<Profile>;
  version: number;
  applied_at: string;
  history: { id: number; new_status: string; employer_note: string | null; created_at: string }[];
  events: Notice[];
};
export type Saved = {
  id: number;
  internship_id: number;
  note: string;
  available: boolean;
  internship: Listing;
};
export type Resume = {
  id: number;
  filename: string;
  parse_state: string;
  extracted: { skills: string[]; coursework: string[]; projects: Project[]; education: string[] };
  failure: string | null;
  profile_version: number;
  created_at: string;
};
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
