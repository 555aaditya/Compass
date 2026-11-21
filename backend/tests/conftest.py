import textwrap
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.session import Base, make_engine


@pytest.fixture
def db():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


SKILLS_MD = textwrap.dedent("""\
    # Tech Stack & Skills

    ## Languages

    | Skill | Depth | Evidence |
    |---|---|---|
    | Python 3.12 | ●●● | Stride, Atlas |
    | TypeScript | ●●● | Stride FE |
    | Go | ● | OSS |

    ## Backend

    | Skill | Depth | Evidence |
    |---|---|---|
    | FastAPI | ●●● | Stride |
    | REST API design | ●●● | Stride |

    ## Data

    | Skill | Depth | Evidence |
    |---|---|---|
    | PostgreSQL/Aurora | ●●● | Atlas |
    | Apache Airflow | ●● | ETL |

    ## Algorithms & CS

    | Skill | Depth | Evidence |
    |---|---|---|
    | Data structures & algorithms | ●●● | DSA |

    ## Do not list (no evidence in any repo)

    | Claimed on GitHub profile | Reality | Action |
    |---|---|---|
    | Redis | One config mention | Remove |
    | Spark / PySpark | Not in any repo | Remove |
""")

PROJECT_MD = textwrap.dedent("""\
    ---
    title: Stock Backtester
    repo: https://github.com/example/backtester
    period: 2026-03
    status: wip
    type: personal
    domains: [quant, backend]
    stack: [Python, Flask, SQLite3]
    resume_strength: A   # lead
    ---

    # Stock Backtester

    > Event-driven backtester in pure Python.

    ## Problem
    text
""")

PROFILE_MD = textwrap.dedent("""\
    # Profile

    ## Links

    | Use | Link |
    |---|---|
    | GitHub | [github.com/example](https://github.com/example) |

    ## Education

    | Institution | Qualification | Score | Years |
    |---|---|---|---|
    | Some University | B.E. Computer Science | 8 CGPA | 2022 to 2026 |
""")

COMPASS_MD = "---\ntitle: Compass\nstack: [Python, Celery, Kafka]\n---\n# Compass\n> The job finder itself.\n"


@pytest.fixture
def wiki(tmp_path: Path) -> Path:
    (tmp_path / "projects").mkdir()
    (tmp_path / "skills.md").write_text(SKILLS_MD)
    (tmp_path / "profile.md").write_text(PROFILE_MD)
    (tmp_path / "projects" / "backtester.md").write_text(PROJECT_MD)
    (tmp_path / "projects" / "compass.md").write_text(COMPASS_MD)
    (tmp_path / "README.md").write_text("# ignore")
    (tmp_path / "claude-memory").mkdir()
    (tmp_path / "claude-memory" / "note.md").write_text("# private")
    return tmp_path
