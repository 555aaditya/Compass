import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorBox, Loading, Pill, ScoreBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function JobDetailPage() {
  const id = Number(useParams().id);
  const { data: j, error, loading, reload } = useAsync(() => api.job(id), [id]);
  const { data: statuses } = useAsync(api.statuses);
  const [err, setErr] = useState<string | null>(null);
  const act = async (fn: () => Promise<unknown>) => { setErr(null); try { await fn(); reload(); } catch (e) { setErr((e as Error).message); } };
  if (loading) return <Loading />;
  if (!j) return <ErrorBox error={error} />;
  const a = j.analysis;
  return (
    <div className="space-y-4">
      <Link to="/jobs" className="text-sm text-indigo-600">← Jobs</Link>
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{j.title}</h2>
            <p className="text-slate-600 dark:text-slate-400">{j.company} · {j.location || "location n/a"} · {j.work_mode} · experience {j.experience_min == null ? "not stated" : `${j.experience_min}+ yrs`}</p>
            <p className="mt-1 text-xs text-slate-500">Found {j.discovered_at.slice(0, 10)} via {j.sources.map((s) => s.source).join(", ")}</p>
          </div>
          <div className="text-right"><ScoreBadge score={j.score} category={j.category} /> <span className="text-sm">{j.category}</span></div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <a className="btn-primary" href={j.apply_url} target="_blank" rel="noreferrer noopener">Open application page</a>
          <button className="btn" onClick={() => act(() => api.setStatus(id, "shortlisted"))}>Shortlist</button>
          <button className="btn" onClick={() => act(() => api.setStatus(id, "not_interested"))}>Not interested</button>
          <button className="btn" onClick={() => act(() => api.generateResume(id))}>Generate resume</button>
          <button className="btn" onClick={() => { if (confirm("Mark as applied? You must submit the application yourself on the employer's site.")) act(() => api.setStatus(id, "applied")); }}>Mark applied</button>
          <select className="input" value={j.status} onChange={(e) => act(() => api.setStatus(id, e.target.value))} aria-label="Update status">
            {statuses?.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div className="mt-2"><ErrorBox error={err} /></div>
      </div>

      {j.eligibility !== "eligible" && (
        <div className="card border-amber-300 text-sm"><b>Eligibility: {j.eligibility}.</b><ul className="list-disc pl-5">{j.eligibility_reasons.map((r) => <li key={r}>{r}</li>)}</ul></div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card text-sm">
          <h3 className="mb-2 font-semibold">Why it matches</h3>
          <ul className="list-disc pl-5">{a.why_matches?.map((w) => <li key={w}>{w}</li>)}</ul>
          <h3 className="mb-1 mt-3 font-semibold">Potential weaknesses</h3>
          <ul className="list-disc pl-5">{a.weaknesses?.length ? a.weaknesses.map((w) => <li key={w}>{w}</li>) : <li>None found</li>}</ul>
          <h3 className="mb-1 mt-3 font-semibold">Recommended resume emphasis</h3><p>{a.recommended_emphasis}</p>
          <h3 className="mb-1 mt-3 font-semibold">Score breakdown</h3>
          <p className="text-slate-600 dark:text-slate-400">{Object.entries(j.score_breakdown).map(([k, v]) => `${k} ${v}`).join(" · ")}</p>
        </div>
        <div className="card text-sm space-y-2">
          <div><h3 className="font-semibold">Matching skills</h3>{a.matching_skills?.map((s) => <span key={s.term} className="mr-1"><Pill tone="green">{s.term} · {s.status.replace("_", " ")}</Pill></span>)}</div>
          <div><h3 className="font-semibold">Missing skills (gaps, never added to resume)</h3>{a.missing_skills?.map((s) => <span key={s.term} className="mr-1"><Pill tone={s.priority === "required" ? "red" : "amber"}>{s.term}</Pill></span>)}
            {a.blocked_skills?.map((s) => <span key={s.term} className="mr-1"><Pill tone="red">{s.term} (do-not-claim)</Pill></span>)}</div>
          <div><h3 className="font-semibold">Relevant projects</h3>{a.relevant_projects?.map((p) => <p key={p.name}>{p.url ? <a className="text-indigo-600" href={p.url} target="_blank" rel="noreferrer noopener">{p.name}</a> : p.name} <span className="text-slate-500">({p.overlap.join(", ")})</span></p>)}</div>
          <div><h3 className="font-semibold">Relevant achievements</h3>{a.relevant_achievements?.length ? a.relevant_achievements.map((x) => <p key={x.name}>{x.name}</p>) : <p className="text-slate-500">None</p>}</div>
        </div>
      </div>

      {j.resumes.length > 0 && (
        <div className="card text-sm"><h3 className="mb-2 font-semibold">Resumes</h3>
          {j.resumes.map((r) => <p key={r.id}>v{r.version} · {r.state}{r.approved && " · approved"} · <Link className="text-indigo-600" to="/resumes">open in Resume Center</Link></p>)}</div>
      )}

      <div className="card"><h3 className="mb-2 font-semibold">Description</h3>
        <div className="mb-2">{j.skills.map((s) => <span key={s.term} className="mr-1"><Pill tone={s.priority === "required" ? "blue" : "slate"}>{s.term} · {s.priority}</Pill></span>)}</div>
        <pre className="whitespace-pre-wrap font-sans text-sm">{j.description || "No description provided by the source."}</pre></div>
    </div>
  );
}
