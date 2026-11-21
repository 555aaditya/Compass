from datetime import datetime, timedelta, timezone

import pytest

from app.services.job_matching.eligibility import evaluate, parse_experience
from app.services.job_matching.preferences import Preferences

P = Preferences()
NOW = datetime.now(timezone.utc)


def ev(title="Software Engineer", loc="Bangalore, India", desc="", posted=None, **kw):
    return evaluate(title, loc, desc, posted or NOW - timedelta(days=2), P, **kw)


@pytest.mark.parametrize("title", ["Senior Software Engineer", "Staff Backend Engineer", "Principal Engineer",
                                    "Engineering Manager", "Tech Lead", "SDE III", "SDE 2"])
def test_senior_titles_rejected(title):
    assert ev(title).status == "rejected"


def test_non_technical_rejected():
    assert ev("Account Executive").status == "rejected"
    assert ev("Technical Recruiter").status == "rejected"


@pytest.mark.parametrize("text,expected", [
    ("3+ years of experience in Python", 3), ("5-8 years of professional experience", 5),
    ("minimum 4 years of relevant experience", 4), ("0-2 years of experience", 0), ("nothing here", None)])
def test_parse_experience(text, expected):
    assert parse_experience(text)[0] == expected


def test_experience_over_limit_rejected_unless_fresher_friendly():
    assert ev(desc="Requires 5+ years of experience.").status == "rejected"
    assert ev(desc="3+ years of experience, freshers also welcome").status == "uncertain"
    assert ev(desc="New grads welcome. Python.").status == "eligible"


def test_unclear_experience_is_uncertain_not_invented():
    e = ev(desc="Build backend services.")
    assert e.status == "uncertain" and e.experience_min is None


def test_location_rules():
    assert ev(loc="Remote - US").status == "rejected"
    assert ev(loc="London, UK").status == "rejected"
    assert ev(loc="Remote", desc="Remote anywhere in the world. 0-2 years.").status == "eligible"
    assert ev(loc="Remote", desc="0-2 years experience").status == "uncertain"
    assert ev(loc="Remote - India", desc="fresher").status == "eligible"
    assert ev(loc="Gurugram; New York", desc="fresher").location_ok == "yes"
    assert ev(loc="", desc="fresher").status == "uncertain"


def test_hybrid_and_work_mode():
    assert ev(loc="Pune (Hybrid)", desc="fresher").work_mode == "hybrid"
    assert ev(loc="Pune", desc="fresher").work_mode == "onsite"


def test_freshness_window_and_unknown_date():
    assert ev(posted=NOW - timedelta(days=40)).status == "rejected"
    e = evaluate("Software Engineer", "Pune", "fresher", None, P)
    assert e.status == "eligible"


def test_unpaid_rejected_unless_enabled():
    assert ev(desc="This is an unpaid role").status == "rejected"


def test_support_and_non_engineering_titles_rejected():
    for t in ("Customer Success Engineer", "Cloud Support Engineer (Night Shift)", "Solutions Architect",
              "Key Account Management", "Candidate Experience Specialist", "Creative Illustrator"):
        assert ev(t, desc="fresher").status == "rejected", t
    for t in ("Associate Software Engineer", "Member of Technical Staff", "Data Scientist", "SDET", "Security Engineer"):
        assert ev(t, desc="fresher").status == "eligible", t
