import type { Company, Job, JobDetail, Overview, Profile, Resume } from "../types/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* keep status text */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json() as Promise<T>;
}
const post = <T,>(path: string, body: unknown = {}) => req<T>(path, { method: "POST", body: JSON.stringify(body) });

export type JobFilters = Record<string, string | number | boolean | undefined>;

export const api = {
  overview: () => req<Overview>("/overview"),
  jobs: (f: JobFilters) => {
    const p = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)));
    return req<{ total: number; items: Job[] }>(`/jobs?${p}`);
  },
  job: (id: number) => req<JobDetail>(`/jobs/${id}`),
  statuses: () => req<string[]>("/statuses"),
  setStatus: (id: number, status: string, note = "") => post<JobDetail>(`/jobs/${id}/status`, { status, note }),
  generateResume: (id: number) => post<Resume>(`/jobs/${id}/resume`),
  resumes: () => req<Resume[]>("/resumes"),
  finalize: (id: number) => post<{ state: string }>(`/resumes/${id}/finalize`),
  approve: (id: number, force = false) => post<Resume>(`/resumes/${id}/approve`, { force }),
  report: (id: number) => req<Record<string, any>>(`/resumes/${id}/report`),
  fileUrl: (id: number, name: string) => `/api/resumes/${id}/files/${name}`,
  fileText: async (id: number, name: string) => (await fetch(`/api/resumes/${id}/files/${name}`)).text(),
  profile: () => req<Profile>("/profile"),
  profileHistory: () => req<any[]>("/profile/history"),
  setVerification: (id: number, v: string) => post(`/profile/evidence/${id}/verification`, { verification: v }),
  settings: () => req<{ preferences: Record<string, any>; environment: Record<string, any> }>("/settings"),
  saveSettings: (body: Record<string, unknown>) => req<Record<string, any>>("/settings", { method: "PUT", body: JSON.stringify(body) }),
  companies: () => req<Company[]>("/companies"),
  addCompany: (c: Partial<Company>) => post("/companies", c),
  patchCompany: (id: number, c: Partial<Company>) => req(`/companies/${id}`, { method: "PATCH", body: JSON.stringify(c) }),
  careerLinks: () => req<{ company: string; url: string }[]>("/career-links"),
  runScan: () => post("/run/scan"),
  runWikiSync: () => post("/run/wiki-sync"),
  scans: () => req<any[]>("/scans"),
};
