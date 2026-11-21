import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_settings
from app.api.routes import router
from app.core.config import Settings
from app.models import Company, Job, JobSkill, ResumeVersion


@pytest.fixture
def client(db, tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, generated_resumes_path=tmp_path, master_resume_path=tmp_path / "nomaster" / "main.tex")
    return TestClient(app)


@pytest.fixture
def jobs(db):
    a = Company(name="Alpha", slug="alpha", ats="greenhouse", board_token="a")
    b = Company(name="Beta", slug="beta", ats="lever", board_token="b")
    db.add_all([a, b]); db.flush()
    rows = [(a, "Backend Engineer", 88, "excellent", "onsite", 0), (a, "Data Engineer", 72, "strong", "hybrid", 1),
            (b, "Software Engineer", 55, "moderate", "remote", None)]
    for i, (c, t, sc, cat, wm, exp) in enumerate(rows):
        j = Job(dedup_key=f"k{i}", company_id=c.id, title=t, title_norm=t.lower(), location="Pune", apply_url=f"https://x/{i}",
                eligibility="eligible", score=sc, category=cat, work_mode=wm, experience_min=exp, analysis={"why_matches": ["x"]})
        j.skills = [JobSkill(term="Python", category="language", priority="required")]
        db.add(j)
    db.commit()


def test_overview_counts(client, jobs):
    o = client.get("/api/overview").json()
    assert o["total_jobs"] == 3 and o["excellent"] == 1 and o["strong"] == 1


def test_filters_and_sorting(client, jobs):
    r = client.get("/api/jobs", params={"min_score": 70}).json()
    assert [j["title"] for j in r["items"]] == ["Backend Engineer", "Data Engineer"]
    assert client.get("/api/jobs", params={"company": "Beta"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"work_mode": "hybrid"}).json()["items"][0]["title"] == "Data Engineer"
    assert client.get("/api/jobs", params={"sort": "company"}).json()["items"][-1]["company"] == "Beta"
    assert client.get("/api/jobs", params={"q": "data"}).json()["total"] == 1
    assert client.get("/api/jobs", params={"max_experience": 0}).json()["total"] == 2  # unknown experience stays visible


def test_status_update_and_history(client, jobs, db):
    jid = client.get("/api/jobs").json()["items"][0]["id"]
    r = client.post(f"/api/jobs/{jid}/status", json={"status": "applied", "note": "via referral"}).json()
    assert r["status"] == "applied" and "referral" in r["notes"]
    assert client.post(f"/api/jobs/{jid}/status", json={"status": "bogus"}).status_code == 422
    assert client.get(f"/api/jobs/{jid}").json()["skills"][0]["term"] == "Python"
    assert client.get("/api/jobs/9999").status_code == 404


def test_settings_persist(client):
    assert client.get("/api/settings").json()["preferences"]["min_match_score"] == 70
    client.put("/api/settings", json={"min_match_score": 80, "freshness_days": 30, "bogus": 1})
    p = client.get("/api/settings").json()["preferences"]
    assert p["min_match_score"] == 80 and p["freshness_days"] == 30 and "bogus" not in p


def test_settings_never_expose_secrets(client):
    env = client.get("/api/settings").json()["environment"]
    assert env["telegram_bot_token"] in ("", "***") and env["email_password"] in ("", "***")


def test_company_crud(client, db):
    assert client.post("/api/companies", json={"name": "Zed", "ats": "ashby", "board_token": "zed"}).status_code == 200
    assert client.post("/api/companies", json={"name": "Zed", "ats": "ashby"}).status_code == 409
    assert client.post("/api/companies", json={"name": "Bad", "ats": "workday"}).status_code == 422
    cid = next(c["id"] for c in client.get("/api/companies").json() if c["name"] == "Zed")
    client.patch(f"/api/companies/{cid}", json={"enabled": False, "priority": 1})
    assert client.delete(f"/api/companies/{cid}").json() == {"deleted": True}


def test_resume_file_whitelist_blocks_traversal(client, jobs, db, tmp_path):
    j = db.query(Job).first()
    (tmp_path / "resume.tex").write_text("x")
    secret = tmp_path.parent / "secret.txt"; secret.write_text("s")
    rv = ResumeVersion(job_id=j.id, directory=str(tmp_path), state="prepared"); db.add(rv); db.commit()
    assert client.get(f"/api/resumes/{rv.id}/files/resume.tex").status_code == 200
    assert client.get(f"/api/resumes/{rv.id}/files/..%2Fsecret.txt").status_code == 404
    assert client.get(f"/api/resumes/{rv.id}/files/resume.pdf").status_code == 404
    assert client.post(f"/api/resumes/{rv.id}/approve", json={}).status_code == 409  # not compiled


def test_generate_resume_without_master_gives_actionable_error(client, jobs):
    jid = client.get("/api/jobs").json()["items"][0]["id"]
    r = client.post(f"/api/jobs/{jid}/resume")
    assert r.status_code == 409 and "import_master" in r.json()["detail"]
