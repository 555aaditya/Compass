import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorBox, Loading, Pill, ScoreBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function Jobs() {
  const [sp, setSp] = useSearchParams();
  const f = Object.fromEntries(sp.entries());
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n); };
  const { data, error, loading } = useAsync(() => api.jobs({ sort: "score", limit: 200, ...f }), [sp.toString()]);
  const { data: statuses } = useAsync(api.statuses);
  const { data: companies } = useAsync(api.companies);
  const [q, setQ] = useState(f.q ?? "");
  useEffect(() => { const t = setTimeout(() => q !== (f.q ?? "") && set("q", q), 300); return () => clearTimeout(t); }, [q]); // eslint-disable-line

  return (
    <div className="space-y-4">
      <div className="card grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-8">
        <input className="input" placeholder="Search title / location" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <select className="input" value={f.min_score ?? ""} onChange={(e) => set("min_score", e.target.value)} aria-label="Minimum score">
          <option value="">Any score</option><option value="85">85+ Excellent</option><option value="70">70+ Strong</option><option value="55">55+ Moderate</option>
        </select>
        <select className="input" value={f.company ?? ""} onChange={(e) => set("company", e.target.value)} aria-label="Company">
          <option value="">All companies</option>{companies?.map((c) => <option key={c.id}>{c.name}</option>)}
        </select>
        <select className="input" value={f.work_mode ?? ""} onChange={(e) => set("work_mode", e.target.value)} aria-label="Work mode">
          <option value="">Any mode</option><option>onsite</option><option>hybrid</option><option>remote</option><option>unknown</option>
        </select>
        <select className="input" value={f.status ?? ""} onChange={(e) => set("status", e.target.value)} aria-label="Status">
          <option value="">Any status</option>{statuses?.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="input" value={f.eligibility ?? ""} onChange={(e) => set("eligibility", e.target.value)} aria-label="Eligibility">
          <option value="">Eligible + uncertain</option><option value="eligible">Eligible only</option><option value="uncertain">Uncertain only</option>
        </select>
        <select className="input" value={f.days ?? ""} onChange={(e) => set("days", e.target.value)} aria-label="Discovered within">
          <option value="">Any date</option><option value="7">Last 7 days</option><option value="14">14 days</option><option value="30">30 days</option>
        </select>
        <select className="input" value={f.sort ?? "score"} onChange={(e) => set("sort", e.target.value)} aria-label="Sort">
          <option value="score">Highest match</option><option value="newest">Newest</option><option value="company">Company</option><option value="role">Role</option>
        </select>
      </div>
      <ErrorBox error={error} />
      {loading && <Loading />}
      {data && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead><tr><th className="th">Score</th><th className="th">Company</th><th className="th">Title</th><th className="th">Location</th>
              <th className="th">Mode</th><th className="th">Exp</th><th className="th">Source</th><th className="th">Found</th><th className="th">Status</th></tr></thead>
            <tbody>
              {data.items.map((j) => (
                <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                  <td className="td"><ScoreBadge score={j.score} category={j.category} /></td>
                  <td className="td">{j.company}</td>
                  <td className="td"><Link className="font-medium text-indigo-600 hover:underline" to={`/jobs/${j.id}`}>{j.title}</Link>
                    {j.eligibility === "uncertain" && <> <Pill tone="amber">uncertain</Pill></>}</td>
                  <td className="td">{j.location}</td><td className="td">{j.work_mode}</td>
                  <td className="td">{j.experience_min == null ? "?" : `${j.experience_min}+`}</td>
                  <td className="td">{j.source}</td><td className="td">{j.discovered_at.slice(0, 10)}</td><td className="td">{j.status}</td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td className="td text-slate-500" colSpan={9}>No jobs match. Eligibility filters are strict by design; widen them in Settings or run a scan.</td></tr>}
            </tbody>
          </table>
          <p className="px-3 py-2 text-xs text-slate-500">{data.total} jobs</p>
        </div>
      )}
    </div>
  );
}
