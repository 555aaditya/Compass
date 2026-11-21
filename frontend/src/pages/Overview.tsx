import { useState } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, Loading, Stat, ago } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function Overview() {
  const { data, error, loading, reload } = useAsync(api.overview);
  const { data: links } = useAsync(api.careerLinks);
  const [msg, setMsg] = useState("");
  const run = async (label: string, fn: () => Promise<unknown>) => {
    setMsg("");
    try { await fn(); setMsg(`${label} started. Refresh in a minute.`); } catch (e) { setMsg((e as Error).message); }
  };
  if (loading) return <Loading />;
  if (!data) return <ErrorBox error={error} />;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => run("Job scan", api.runScan)}>Run job scan</button>
        <button className="btn" onClick={() => run("Wiki sync", api.runWikiSync)}>Sync wiki</button>
        <button className="btn" onClick={reload}>Refresh</button>
        <Link className="btn" to="/jobs?status=shortlisted">View shortlisted</Link>
        {msg && <span className="self-center text-sm text-slate-500">{msg}</span>}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        <Stat label="Jobs discovered" value={data.total_jobs} />
        <Stat label="New this week" value={data.new_jobs} />
        <Stat label="Excellent" value={data.excellent} />
        <Stat label="Strong" value={data.strong} />
        <Stat label="Shortlisted" value={data.shortlisted} />
        <Stat label="Applied" value={data.applied} />
        <Stat label="Interviews" value={data.interviews} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card text-sm">
          <p>Last successful scan: <b>{ago(data.last_scan?.at)}</b>{data.last_scan && ` (${data.last_scan.new} new)`}</p>
          <p>Last wiki sync: <b>{ago(data.last_wiki_sync?.at)}</b>{data.last_wiki_sync && ` (${data.last_wiki_sync.pages} pages)`}</p>
        </div>
        <div className="card text-sm">
          <h2 className="mb-2 font-semibold">Recent notifications</h2>
          {data.recent_notifications.length === 0 && <p className="text-slate-500">None yet.</p>}
          {data.recent_notifications.map((n) => (
            <p key={`${n.job_id}${n.channel}`}><Link className="text-indigo-600" to={`/jobs/${n.job_id}`}>Job {n.job_id}</Link> via {n.channel}: {n.status}, {ago(n.at)}</p>
          ))}
        </div>
      </div>
      <div className="card text-sm">
        <h2 className="mb-1 font-semibold">Career pages the app cannot scan</h2>
        <p className="mb-2 text-slate-500">These sites block automated clients or have no public feed. Open the pre-filtered search yourself.</p>
        <div className="flex flex-wrap gap-2">
          {links?.map((l) => <a key={l.company} className="btn" href={l.url} target="_blank" rel="noreferrer noopener">{l.company}</a>)}
        </div>
      </div>
    </div>
  );
}
