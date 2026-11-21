import type { ReactNode } from "react";

const CAT: Record<string, string> = {
  excellent: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  strong: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  low: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export function ScoreBadge({ score, category }: { score: number | null; category: string | null }) {
  if (score == null) return <span className="text-slate-400">–</span>;
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${CAT[category ?? "low"] ?? CAT.low}`}>{score.toFixed(0)}</span>;
}

export function Pill({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "green" | "red" | "amber" | "blue" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    red: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
    amber: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    blue: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  };
  return <span className={`inline-block rounded px-2 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="card">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200">{error}</div> : null;
}

export function Loading() { return <p className="text-sm text-slate-500">Loading…</p>; }

export function ago(iso?: string | null) {
  if (!iso) return "never";
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  return m < 60 ? `${m}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`;
}
