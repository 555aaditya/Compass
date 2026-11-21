import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Jobs from "./pages/Jobs";
import { ScoreBadge, ago } from "./components/ui";

const jobs = { total: 2, items: [
  { id: 1, company: "Acme", title: "Backend Engineer", location: "Pune", work_mode: "hybrid", experience_min: 0, score: 88, category: "excellent",
    status: "discovered", eligibility: "eligible", eligibility_reasons: [], discovered_at: "2026-11-20T00:00:00Z", posted_at: null, source: "greenhouse", apply_url: "https://x", active: true },
  { id: 2, company: "Beta", title: "Data Engineer", location: "Remote", work_mode: "remote", experience_min: null, score: 61, category: "moderate",
    status: "shortlisted", eligibility: "uncertain", eligibility_reasons: ["Remote but eligibility for India not stated"], discovered_at: "2026-11-21T00:00:00Z", posted_at: null, source: "lever", apply_url: "https://y", active: true },
]};

afterEach(() => vi.restoreAllMocks());

describe("Jobs page", () => {
  it("renders jobs, flags uncertain eligibility and passes filters to the API", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      calls.push(url);
      const body = url.startsWith("/api/jobs?") ? jobs : url.includes("statuses") ? ["discovered", "shortlisted"] : [];
      return new Response(JSON.stringify(body), { status: 200 });
    }));
    render(<MemoryRouter initialEntries={["/jobs?min_score=70&work_mode=hybrid"]}><Jobs /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText("Backend Engineer")).toBeTruthy());
    expect(screen.getByText("uncertain")).toBeTruthy();
    expect(screen.getByText("88")).toBeTruthy();
    const jobCall = calls.find((c) => c.startsWith("/api/jobs?"))!;
    expect(jobCall).toContain("min_score=70");
    expect(jobCall).toContain("work_mode=hybrid");
  });

  it("surfaces API errors instead of failing silently", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "boom" }), { status: 500 })));
    render(<MemoryRouter><Jobs /></MemoryRouter>);
    await waitFor(() => expect(screen.getAllByRole("alert")[0].textContent).toContain("boom"));
  });
});

describe("ui helpers", () => {
  it("ScoreBadge shows a dash without a score", () => {
    render(<ScoreBadge score={null} category={null} />);
    expect(screen.getByText("–")).toBeTruthy();
  });
  it("ago handles missing values", () => expect(ago(null)).toBe("never"));
});
