from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import Settings
from app.workers.pipeline import run_scan_pipeline, run_wiki_sync


def build_scheduler(s: Settings) -> BackgroundScheduler:
    sch = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600})
    sch.add_job(run_scan_pipeline, "interval", hours=s.job_scan_interval_hours, id="scan", args=[s])
    sch.add_job(run_wiki_sync, "interval", hours=s.wiki_sync_interval_hours, id="wiki", args=[s])
    return sch
