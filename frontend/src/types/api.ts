export interface Job {
  id: number; company: string; title: string; location: string; work_mode: string; experience_min: number | null;
  score: number | null; category: string | null; status: string; eligibility: string; eligibility_reasons: string[];
  discovered_at: string; posted_at: string | null; source: string | null; apply_url: string; active: boolean;
}
export interface SkillMatch { term: string; priority: string; status: string; evidence: string[] }
export interface JobDetail extends Job {
  description: string; notes: string; skills: { term: string; category: string; priority: string }[];
  sources: { source: string; url: string }[]; score_breakdown: Record<string, number>; resumes: Resume[];
  analysis: {
    flavor?: string; matching_skills?: SkillMatch[]; missing_skills?: SkillMatch[]; blocked_skills?: SkillMatch[];
    relevant_projects?: { name: string; url: string; overlap: string[] }[];
    relevant_achievements?: { name: string }[]; why_matches?: string[]; weaknesses?: string[];
    recommended_emphasis?: string; competitive_programming_relevance?: boolean; research_relevance?: boolean;
  };
}
export interface Resume {
  id: number; job_id: number; company: string; title: string; score: number | null; version: number;
  state: string; approved: boolean; created_at: string; files: string[];
}
export interface Overview {
  total_jobs: number; new_jobs: number; excellent: number; strong: number; shortlisted: number; applied: number;
  interviews: number; last_scan: { at: string; new: number } | null; last_wiki_sync: { at: string; pages: number } | null;
  recent_notifications: { job_id: number; channel: string; status: string; at: string }[];
}
export interface EvidenceItem {
  name: string; description: string; level: string; evidence: string; source_path: string; source_url: string;
  verification: string; extra: Record<string, unknown>;
}
export type Profile = Record<string, EvidenceItem[]>;
export interface Company {
  id: number; name: string; ats: string; board_token: string; region: string; priority: number; enabled: boolean;
  last_ok_at: string | null; last_error: string | null; failures: number;
}
