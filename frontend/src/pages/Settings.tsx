import { useEffect, useState } from "react";
import { ErrorBox, Loading, Pill, ago } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function Settings() {
  const { data, error, loading } = useAsync(api.settings);
  const { data: companies, reload: reloadCo } = useAsync(api.companies);
  const { data: scans } = useAsync(api.scans);
  const [p, setP] = useState<Record<string, any>>({});
  const [msg, setMsg] = useState("");
  const [co, setCo] = useState({ name: "", ats: "greenhouse", board_token: "" });
  useEffect(() => { if (data) setP(data.preferences); }, [data]);
  if (loading) return <Loading />;
  if (!data) return <ErrorBox error={error} />;
  const save = async () => { try { await api.saveSettings(p); setMsg("Saved."); } catch (e) { setMsg((e as Error).message); } };
  const num = (k: string) => <input className="input w-24" type="number" value={p[k] ?? ""} onChange={(e) => setP({ ...p, [k]: Number(e.target.value) })} />;
  const ch = p.notification_channels ?? {};
  return (
    <div className="space-y-6">
      <section className="card space-y-3 text-sm">
        <h2 className="font-semibold">Job preferences</h2>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <label>Max experience (years) {num("max_experience_years")}</label>
          <label>Freshness window
            <select className="input ml-2" value={p.freshness_days} onChange={(e) => setP({ ...p, freshness_days: Number(e.target.value) })}>{[7, 14, 30, 60].map((d) => <option key={d} value={d}>{d} days</option>)}</select></label>
          <label>Notification threshold {num("min_match_score")}</label>
          <label>Daily notification limit {num("daily_notification_limit")}</label>
        </div>
        <div className="flex flex-wrap gap-4">
          {["telegram", "email", "whatsapp"].map((c) => (
            <label key={c}><input type="checkbox" checked={!!ch[c]} onChange={(e) => setP({ ...p, notification_channels: { ...ch, [c]: e.target.checked } })} /> {c}</label>
          ))}
          <label><input type="checkbox" checked={!!p.include_uncertain} onChange={(e) => setP({ ...p, include_uncertain: e.target.checked })} /> show uncertain jobs</label>
        </div>
        <label className="block">Target roles (comma separated)
          <textarea className="input mt-1 w-full" rows={3} value={(p.target_roles ?? []).join(", ")} onChange={(e) => setP({ ...p, target_roles: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} /></label>
        <label className="block">Score weights (must sum to a meaningful total; default 100)
          <div className="mt-1 flex flex-wrap gap-3">{Object.keys(p.weights ?? {}).map((k) => (
            <span key={k}>{k} <input className="input w-16" type="number" value={p.weights[k]} onChange={(e) => setP({ ...p, weights: { ...p.weights, [k]: Number(e.target.value) } })} /></span>))}</div></label>
        <div><button className="btn-primary" onClick={save}>Save</button> <span className="ml-2 text-slate-500">{msg}</span></div>
      </section>

      <section className="card overflow-x-auto p-0">
        <h2 className="px-4 pt-4 font-semibold">Company watchlist & source health</h2>
        <table className="w-full"><thead><tr><th className="th">Company</th><th className="th">Source</th><th className="th">Priority</th><th className="th">Enabled</th><th className="th">Health</th></tr></thead>
          <tbody>{companies?.map((c) => (
            <tr key={c.id} className="border-t border-slate-100 dark:border-slate-800">
              <td className="td">{c.name}</td><td className="td">{c.ats}{c.board_token && ` / ${c.board_token}`}</td>
              <td className="td"><input className="input w-16" type="number" min={1} max={10} defaultValue={c.priority} onBlur={(e) => api.patchCompany(c.id, { priority: Number(e.target.value) })} /></td>
              <td className="td"><input type="checkbox" disabled={c.ats === "manual"} defaultChecked={c.enabled} onChange={(e) => api.patchCompany(c.id, { enabled: e.target.checked }).then(reloadCo)} aria-label={`Enable ${c.name}`} /></td>
              <td className="td">{c.ats === "manual" ? <Pill>no public API</Pill> : c.last_error ? <Pill tone="red">{c.failures} failures</Pill> : c.last_ok_at ? <Pill tone="green">ok {ago(c.last_ok_at)}</Pill> : <Pill>not scanned</Pill>}</td>
            </tr>))}</tbody></table>
        <form className="flex flex-wrap gap-2 p-4 text-sm" onSubmit={async (e) => { e.preventDefault(); try { await api.addCompany(co); setCo({ name: "", ats: "greenhouse", board_token: "" }); reloadCo(); } catch (er) { setMsg((er as Error).message); } }}>
          <input className="input" placeholder="Company" value={co.name} onChange={(e) => setCo({ ...co, name: e.target.value })} required />
          <select className="input" value={co.ats} onChange={(e) => setCo({ ...co, ats: e.target.value })}><option>greenhouse</option><option>lever</option><option>ashby</option></select>
          <input className="input" placeholder="Board token (e.g. stripe)" value={co.board_token} onChange={(e) => setCo({ ...co, board_token: e.target.value })} required />
          <button className="btn">Add company</button>
        </form>
      </section>

      <section className="card text-sm">
        <h2 className="mb-2 font-semibold">Recent scans</h2>
        {scans?.slice(0, 5).map((s) => <p key={s.id}>{s.started_at.slice(0, 16).replace("T", " ")} · {s.status} · fetched {s.fetched}, new {s.new}, kept {s.eligible}, notified {s.notified}</p>)}
      </section>

      <section className="card text-sm">
        <h2 className="mb-2 font-semibold">Environment (secrets hidden; edit <code>.env</code> to change)</h2>
        <pre className="overflow-x-auto text-xs">{JSON.stringify(data.environment, null, 2)}</pre>
      </section>
    </div>
  );
}
