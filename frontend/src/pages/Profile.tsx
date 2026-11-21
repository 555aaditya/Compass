import { useState } from "react";
import { ErrorBox, Loading, Pill } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

const ORDER = ["education", "experience", "projects", "programming_languages", "frameworks", "libraries", "databases", "cloud_and_devops",
  "data_engineering", "computer_science_fundamentals", "competitive_programming", "research_and_publications", "certifications", "achievements"];
const LEVEL: Record<string, string> = { deep: "●●●", used: "●●", touched: "●" };

export default function Profile() {
  const { data, error, loading } = useAsync(api.profile);
  const { data: hist } = useAsync(api.profileHistory);
  const [showDisputed, setShowDisputed] = useState(false);
  if (loading) return <Loading />;
  if (!data) return <ErrorBox error={error} />;
  const cats = [...ORDER.filter((c) => data[c]), ...Object.keys(data).filter((c) => !ORDER.includes(c) && c !== "disputed_claims" && c !== "contact")];
  const last = hist?.[0];
  return (
    <div className="space-y-4">
      <div className="card text-sm">
        Built from the Quant-Journal Resume Wiki. Last sync: <b>{last ? `${last.started_at.slice(0, 16).replace("T", " ")} (${last.status})` : "never"}</b>
        {last && <> · +{last.added.length} / ~{last.modified.length} / −{last.deleted.length} pages</>}
        {last?.warnings?.map((w: string) => <p key={w} className="text-amber-700 dark:text-amber-300">⚠ {w}</p>)}
        {last?.error && <p className="text-rose-700">{last.error}</p>}
      </div>
      {cats.map((c) => (
        <section key={c} className="card">
          <h2 className="mb-2 font-semibold capitalize">{c.replaceAll("_", " ")} <span className="text-sm font-normal text-slate-500">({data[c].length})</span></h2>
          <ul className="space-y-1 text-sm">
            {data[c].map((e) => (
              <li key={e.name}>
                {e.level && <span className="mr-2 text-indigo-600">{LEVEL[e.level]}</span>}
                <b>{e.name}</b>
                {e.verification !== "verified" && <> <Pill tone="amber">{e.verification}</Pill></>}
                {e.description && <span className="text-slate-600 dark:text-slate-400"> · {e.description.slice(0, 160)}</span>}
                {" "}<a className="text-xs text-indigo-600" href={e.source_url || undefined} target="_blank" rel="noreferrer noopener">{e.source_path}</a>
              </li>
            ))}
          </ul>
        </section>
      ))}
      <section className="card">
        <button className="font-semibold" onClick={() => setShowDisputed(!showDisputed)}>{showDisputed ? "▼" : "▶"} Do-not-claim list ({data.disputed_claims?.length ?? 0})</button>
        {showDisputed && <ul className="mt-2 list-disc pl-5 text-sm">{data.disputed_claims?.map((d) => <li key={d.source_path + d.name}><b>{d.name}</b>: {d.description} <span className="text-xs text-slate-500">{d.source_path}</span></li>)}</ul>}
      </section>
    </div>
  );
}
