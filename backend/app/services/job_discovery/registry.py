from app.services.job_discovery.ashby import AshbyAdapter
from app.services.job_discovery.greenhouse import GreenhouseAdapter
from app.services.job_discovery.lever import LeverAdapter

ADAPTERS = {a.name: a for a in (GreenhouseAdapter(), LeverAdapter(), AshbyAdapter())}
