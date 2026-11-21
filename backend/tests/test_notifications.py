import httpx
from sqlalchemy import select

from app.core.config import Settings
from app.models import Company, Job, Notification
from app.services.job_matching.preferences import Preferences
from app.services.notifications.channels import ChannelError, EmailChannel, TelegramChannel, build_channels
from app.services.notifications.service import format_message, notify_new_matches


class Fake:
    def __init__(self, name="telegram", fail_times=0, configured=True):
        self.name, self.fail_times, self._c, self.sent = name, fail_times, configured, []

    def configured(self): return self._c

    def send(self, subject, body):
        if self.fail_times:
            self.fail_times -= 1
            raise ChannelError("boom")
        self.sent.append((subject, body))


def make_job(db, score=80, eligibility="eligible"):
    c = db.scalar(select(Company).where(Company.name == "Acme"))
    if c is None:
        c = Company(name="Acme", slug="acme", ats="greenhouse", board_token="a")
        db.add(c); db.flush()
    j = Job(dedup_key=f"k{score}{eligibility}", company_id=c.id, title="Software Engineer", title_norm="software engineer",
            location="Pune", apply_url="https://acme/jobs/1", eligibility=eligibility, score=score, category="strong",
            analysis={"why_matches": ["Matches Python"], "matching_skills": [{"term": "Python"}],
                      "missing_skills": [{"term": "Go"}], "relevant_projects": [{"name": "Stride"}]},
            experience_min=0, work_mode="onsite")
    db.add(j); db.commit()
    return j


def test_message_contains_required_fields(db):
    subject, body = format_message(make_job(db), None, "http://localhost:5173")
    for needle in ("Acme", "Software Engineer", "Pune", "80/100", "Python", "Go", "Stride", "https://acme/jobs/1", "not prepared", "/jobs/"):
        assert needle in body or needle in subject


def test_sent_once_per_channel_and_below_threshold_skipped(db):
    make_job(db, 80); 
    low = make_job(db, 60)
    tg = Fake()
    prefs = Preferences()
    assert notify_new_matches(db, {"telegram": tg}, prefs) == 1
    assert notify_new_matches(db, {"telegram": tg}, prefs) == 0  # no duplicate alert
    assert len(tg.sent) == 1 and low.id not in [n.job_id for n in db.scalars(select(Notification))]


def test_uncertain_jobs_are_never_notified(db):
    make_job(db, 80, "uncertain")
    assert notify_new_matches(db, {"telegram": Fake()}, Preferences()) == 0


def test_disabled_or_unconfigured_channels_skipped(db):
    make_job(db)
    prefs = Preferences(); prefs.notification_channels = {"telegram": False, "email": True}
    em = Fake("email", configured=False)
    assert notify_new_matches(db, {"telegram": Fake(), "email": em}, prefs) == 0


def test_failed_delivery_retries_then_recovers(db):
    make_job(db)
    tg = Fake(fail_times=2)
    assert notify_new_matches(db, {"telegram": tg}, Preferences(), sleep=lambda s: None) == 1
    n = db.scalar(select(Notification))
    assert n.status == "sent" and n.attempts == 3


def test_permanent_failure_is_recorded_and_retried_next_run(db):
    make_job(db)
    tg = Fake(fail_times=99)
    assert notify_new_matches(db, {"telegram": tg}, Preferences(), sleep=lambda s: None) == 0
    assert db.scalar(select(Notification)).status == "failed"
    tg.fail_times = 0
    assert notify_new_matches(db, {"telegram": tg}, Preferences()) == 1


def test_daily_limit(db):
    for s in (80, 81, 82): make_job(db, s)
    prefs = Preferences(); prefs.daily_notification_limit = 2
    assert notify_new_matches(db, {"telegram": Fake()}, prefs) == 2


def test_telegram_error_does_not_leak_token():
    s = Settings(telegram_bot_token="123456:ABC-secret-token-value-0123456789abcdef", telegram_chat_id="1")
    def boom(req): raise httpx.ConnectError("x", request=req)
    ch = TelegramChannel(s, httpx.Client(transport=httpx.MockTransport(boom)))
    try:
        ch.send("a", "b")
    except ChannelError as exc:
        assert "secret" not in str(exc)


def test_email_and_whatsapp_configuration_gates():
    ch = build_channels(Settings(_env_file=None))
    assert not any(c.configured() for c in ch.values())
    s = Settings(_env_file=None, smtp_host="h", email_address="a@b.c", email_password="p")
    sent = {}
    class SMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, u, p): sent["login"] = u
        def send_message(self, m): sent["to"] = m["To"]
    EmailChannel(s, SMTP).send("s", "b")
    assert sent == {"login": "a@b.c", "to": "a@b.c"}
