from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.models import Company, Job, JobSource, ScanHistory
from app.services.candidate_profile.sync import sync_wiki
from app.services.job_discovery.ashby import AshbyAdapter
from app.services.job_discovery.base import SourceError, get_json
from app.services.job_discovery.greenhouse import GreenhouseAdapter
from app.services.job_discovery.lever import LeverAdapter
from app.services.job_discovery.scan import run_scan
from app.services.job_discovery.store import dedup_key, seed_companies

RECENT = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

GH = {"jobs": [
    {"id": 1, "title": "Software Engineer, New Grad", "absolute_url": "https://x/1", "first_published": RECENT,
     "location": {"name": "Bengaluru, India"},
     "content": "&lt;h3&gt;Requirements&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Python and FastAPI&lt;/li&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;&lt;h3&gt;Nice to have&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Kubernetes&lt;/li&gt;&lt;li&gt;Redis&lt;/li&gt;&lt;/ul&gt; 0-2 years of experience"},
    {"id": 2, "title": "Senior Backend Engineer", "absolute_url": "https://x/2", "first_published": RECENT,
     "location": {"name": "Bengaluru, India"}, "content": "5+ years"},
    {"id": 3, "title": "Software Engineer", "absolute_url": "https://x/3", "first_published": RECENT,
     "location": {"name": "San Francisco, CA"}, "content": "new grad"},
    {"id": 4, "title": "", "absolute_url": "", "location": {"name": "Pune"}, "content": ""},
]}
LEVER = [{"id": "a1", "text": "Backend Engineer", "hostedUrl": "https://l/a1", "createdAt": 1_900_000_000_000,
          "categories": {"location": "Gurugram"}, "descriptionPlain": "Entry level. Python.", "workplaceType": "hybrid"}]
ASHBY = {"jobs": [{"id": "z", "title": "Software Engineer", "jobUrl": "https://a/z", "isListed": True,
                   "location": "Remote - India", "isRemote": True, "publishedAt": RECENT,
                   "descriptionPlain": "Fresher friendly. Python.", "address": {"postalAddress": {"addressCountry": "India"}}},
                  {"id": "h", "title": "Hidden", "jobUrl": "https://a/h", "isListed": False}]}


def transport(handler_map):
    def handler(req: httpx.Request):
        for frag, (code, body) in handler_map.items():
            if frag in str(req.url):
                return httpx.Response(code, json=body)
        return httpx.Response(404, json={})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_greenhouse_adapter_unescapes_html_and_parses_dates():
    jobs = GreenhouseAdapter().fetch("Acme", "acme", transport({"greenhouse": (200, GH)}))
    assert jobs[0].location == "Bengaluru, India" and "- Python and FastAPI" in jobs[0].description_text
    assert "<" not in jobs[0].description_text and jobs[0].posted_at is not None


def test_lever_and_ashby_adapters():
    lj = LeverAdapter().fetch("L", "l", transport({"lever": (200, LEVER)}))
    assert lj[0].posted_at.year >= 2030 - 1 and lj[0].location == "Gurugram"
    aj = AshbyAdapter().fetch("A", "a", transport({"ashbyhq": (200, ASHBY)}))
    assert len(aj) == 1 and aj[0].remote_flag and aj[0].country == "India"  # unlisted posting skipped


def test_get_json_retries_then_raises(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = []
    def h(req):
        calls.append(1)
        return httpx.Response(503)
    with pytest.raises(SourceError):
        get_json(httpx.Client(transport=httpx.MockTransport(h)), "https://x/y", attempts=3)
    assert len(calls) == 3


def test_get_json_404_is_not_retried():
    calls = []
    def h(req):
        calls.append(1)
        return httpx.Response(404)
    with pytest.raises(SourceError):
        get_json(httpx.Client(transport=httpx.MockTransport(h)), "https://x/y")
    assert len(calls) == 1


def test_dedup_key_ignores_case_and_secondary_locations():
    a = dedup_key("acme", "Software Engineer (Backend)", "Pune; Mumbai")
    assert a == dedup_key("acme", "software engineer", "pune")
    assert a != dedup_key("acme", "software engineer", "delhi")


def test_seed_marks_manual_companies_disabled(db):
    seed_companies(db)
    assert seed_companies(db) == 0  # idempotent
    g = db.scalar(select(Company).where(Company.name == "Google"))
    assert g.ats == "manual" and not g.enabled
    assert db.scalar(select(Company).where(Company.name == "Stripe")).enabled


def test_end_to_end_scan_filters_scores_and_dedups(db, wiki):
    sync_wiki(db, wiki, {"projects/compass.md"})
    seed_companies(db)
    for c in db.scalars(select(Company)):
        c.enabled = c.name in ("Stripe", "CRED")
    db.commit()
    client = transport({"boards-api.greenhouse.io": (200, GH), "api.lever.co": (200, LEVER)})
    scan = run_scan(db, client=client)
    assert scan.status == "ok" and scan.fetched == 5
    jobs = {j.title: j for j in db.scalars(select(Job))}
    assert set(jobs) == {"Software Engineer, New Grad", "Backend Engineer"}  # senior, US-based and blank skipped
    j = jobs["Software Engineer, New Grad"]
    assert j.eligibility == "eligible" and j.score > 50
    terms = {m["term"]: m["status"] for m in j.analysis["matching_skills"]}
    assert terms["Python"] == "demonstrated" and terms["FastAPI"] == "demonstrated"
    gaps = {m["term"] for m in j.analysis["missing_skills"]}
    assert "Kubernetes" in gaps
    assert {b["term"] for b in j.analysis["blocked_skills"]} == {"Redis"}  # on the do-not-claim list
    assert db.scalar(select(JobSource).where(JobSource.job_id == j.id))

    # rescan: no duplicates, jobs stay active
    run_scan(db, client=client)
    assert len(db.scalars(select(Job)).all()) == 2

    # a posting that disappears from a healthy board is expired
    GH["jobs"].pop(0)
    run_scan(db, client=client)
    assert db.scalar(select(Job).where(Job.title == "Software Engineer, New Grad")).status == "expired"


def test_source_failure_is_isolated_and_tracked(db, wiki, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    sync_wiki(db, wiki)
    seed_companies(db)
    for c in db.scalars(select(Company)):
        c.enabled = c.name in ("Stripe", "CRED")
    db.commit()
    client = transport({"boards-api.greenhouse.io": (500, {}), "api.lever.co": (200, LEVER)})
    scan = run_scan(db, client=client)
    assert scan.source_results["Stripe"]["error"] and scan.source_results["CRED"]["kept"] == 1
    assert db.scalar(select(Company).where(Company.name == "Stripe")).consecutive_failures == 1
    assert scan.status == "ok"


def test_smartrecruiters_prefilters_before_fetching_details():
    from app.services.job_discovery.smartrecruiters import SmartRecruitersAdapter
    lst = {"totalFound": 3, "content": [
        {"id": "1", "name": "Software Engineer", "releasedDate": RECENT, "location": {"city": "Bengaluru", "country": "in"}},
        {"id": "2", "name": "Senior Software Engineer", "releasedDate": RECENT, "location": {"city": "Bengaluru", "country": "in"}},
        {"id": "3", "name": "Software Engineer", "releasedDate": RECENT, "location": {"city": "Austin", "country": "us"}}]}
    detail = {"postingUrl": "https://jobs.smartrecruiters.com/acme/1", "jobAd": {"sections": {"jobDescription": {"text": "<p>Python, fresher</p>"}}}}
    seen = []
    def h(req):
        seen.append(req.url.path)
        return httpx.Response(200, json=detail if req.url.path.endswith("/1") else lst)
    out = SmartRecruitersAdapter().fetch("Acme", "acme", httpx.Client(transport=httpx.MockTransport(h)))
    assert [j.external_id for j in out] == ["1"] and "Python" in out[0].description_text
    assert not any(p.endswith(("/2", "/3")) for p in seen)  # rejected postings never cost a detail request


def test_seed_upgrades_previously_unsupported_company(db):
    from app.models import Company
    db.add(Company(name="Swiggy", slug="swiggy", ats="manual", board_token="", enabled=False)); db.commit()
    seed_companies(db)
    c = db.scalar(select(Company).where(Company.name == "Swiggy"))
    assert (c.ats, c.board_token, c.enabled) == ("smartrecruiters", "swiggy", True)


def test_amazon_and_atlassian_adapters():
    from app.services.job_discovery.careers import AmazonAdapter, AtlassianAdapter
    am = {"hits": 1, "jobs": [{"id_icims": "99", "title": "SDE I", "job_path": "/en/jobs/99/sde-i", "normalized_location": "Bengaluru, Karnataka, IND",
                               "description": "<p>Build</p>", "basic_qualifications": "- Python", "posted_date": "November 20, 2026", "country_code": "IND"}]}
    seen = {}
    def h(req):
        seen["q"] = str(req.url)
        return httpx.Response(200, json=am)
    j = AmazonAdapter().fetch("Amazon", "IND", httpx.Client(transport=httpx.MockTransport(h)))[0]
    assert "normalized_country_code" in seen["q"] and j.url == "https://www.amazon.jobs/en/jobs/99/sde-i" and j.posted_at.year == 2026
    at = [{"id": 5, "title": "Backend Engineer", "locations": ["Remote - India - Remote"], "overview": "<p>fresher</p>",
           "portalJobPost": {"portalUrl": "https://careers/5", "updatedDate": "2026-11-20 07:14 AM"}}]
    a = AtlassianAdapter().fetch("Atlassian", "", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=at))))[0]
    assert a.remote_flag and a.url == "https://careers/5" and "India" in a.location
