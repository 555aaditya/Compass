import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, Loading, Pill } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Resume } from "../types/api";

function Report({ r }: { r: Resume }) {
  const { data, error } = useAsync(() => api.report(r.id), [r.id]);
  if (error) return <p className="text-sm text-slate-500">{error}</p>;
  if (!data) return <Loading />;
  const cov = data.keyword_coverage, v = data.validation;
  return (
    <div className="mt-2 space-y-2 text-sm">
      <p className="text-xs text-slate-500">{data.disclaimer}</p>
      <p>Required keywords in resume: <b>{cov.required.matched_in_resume}/{cov.required.total}</b> ({cov.required.supported} supported by evidence). Preferred: <b>{cov.preferred.matched_in_resume}/{cov.preferred.total}</b>.
        Gaps: {cov.unsupported_requirements.join(", ") || "none"}.</p>
      <div className="flex flex-wrap gap-1">{v.checks.map((c: any) => <span key={c.name} title={c.detail}><Pill tone={c.status === "pass" ? "green" : c.status === "warn" ? "amber" : "red"}>{c.name}</Pill></span>)}</div>
      {data.claim_violations.length > 0 && <ul className="list-disc pl-5 text-rose-700 dark:text-rose-300">{data.claim_violations.map((x: any, i: number) => <li key={i}>[{x.severity}] <code>{x.text}</code>: {x.reason}</li>)}</ul>}
    </div>
  );
}

export default function Resumes() {
  const { data, error, loading, reload } = useAsync(api.resumes);
  const [open, setOpen] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const act = async (fn: () => Promise<unknown>) => { setMsg(null); try { await fn(); reload(); } catch (e) { setMsg((e as Error).message); } };
  if (loading) return <Loading />;
  return (
    <div className="space-y-4">
      <div className="card text-sm">
        <b>Master resume is read-only.</b> This app never edits it and never submits applications. Tailoring workflow: generate a workspace,
        edit <code>resume.tex</code> in a Claude Code session following <code>TAILOR.md</code>, then Finalize to compile and validate.
      </div>
      <ErrorBox error={error ?? msg} />
      {data?.length === 0 && <p className="text-sm text-slate-500">No resumes yet. Open a job and press “Generate resume”.</p>}
      {data?.map((r) => (
        <div key={r.id} className="card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><Link className="font-semibold text-indigo-600" to={`/jobs/${r.job_id}`}>{r.title}</Link> at {r.company}
              <span className="ml-2 text-sm text-slate-500">v{r.version} · score {r.score?.toFixed(0) ?? "–"} · {r.created_at.slice(0, 10)}</span></div>
            <div className="flex items-center gap-2"><Pill tone={r.approved ? "green" : r.state === "failed" ? "red" : r.state === "compiled" ? "blue" : "slate"}>{r.approved ? "approved" : r.state}</Pill></div>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-sm">
            <button className="btn" onClick={() => act(() => api.finalize(r.id))}>Finalize (compile + validate)</button>
            <button className="btn" onClick={() => act(async () => { try { await api.approve(r.id); } catch (e) {
              if (confirm(`${(e as Error).message}\n\nApprove anyway? You are vouching for these claims.`)) await api.approve(r.id, true); else throw e; } })}>Approve</button>
            <button className="btn" onClick={() => setOpen(open === r.id ? null : r.id)}>{open === r.id ? "Hide" : "ATS report"}</button>
            {r.files.includes("resume.pdf") && <a className="btn" href={api.fileUrl(r.id, "resume.pdf")} target="_blank" rel="noreferrer">PDF</a>}
            {["resume.tex", "changes.md", "ats_report.md", "extracted_resume.txt"].filter((f) => r.files.includes(f)).map((f) =>
              <a key={f} className="btn" href={api.fileUrl(r.id, f)} target="_blank" rel="noreferrer">{f}</a>)}
          </div>
          {open === r.id && <Report r={r} />}
        </div>
      ))}
    </div>
  );
}
