"""Skill vocabulary: canonical term -> (category, regex aliases). Shared by job and candidate sides."""
import re

# (canonical, category, pattern)
_TERMS = [
    ("Python", "language", r"python"), ("Java", "language", r"java(?!\s*script)"),
    ("JavaScript", "language", r"javascript|\bjs\b|ecmascript"), ("TypeScript", "language", r"typescript"),
    ("Go", "language", r"golang|\bgo\b(?=\s*(?:lang|programming|services|backend|,|/))"),
    ("C++", "language", r"c\+\+|cpp"), ("C#", "language", r"c#|\.net"), ("Rust", "language", r"\brust\b"),
    ("Kotlin", "language", r"kotlin"), ("Scala", "language", r"\bscala\b"), ("Ruby", "language", r"\bruby\b"),
    ("SQL", "language", r"\bsql\b|\bt-sql\b|\bpl/sql\b"), ("Bash", "language", r"\bbash\b|shell script"),
    ("FastAPI", "framework", r"fastapi"), ("Django", "framework", r"django"), ("Flask", "framework", r"flask"),
    ("Spring Boot", "framework", r"spring\s*boot|\bspring\b"), ("Node.js", "framework", r"node\.?js|\bnode\b|express(?:\.js)?"),
    ("React", "framework", r"\breact(?:\.js|js)?\b"), ("Angular", "framework", r"angular"), ("Vue", "framework", r"\bvue(?:\.js)?\b"),
    ("Next.js", "framework", r"next\.?js"), ("GraphQL", "framework", r"graphql"),
    ("REST APIs", "concept", r"\brest(?:ful)?\b|rest\s*apis?|\bapis?\b"), ("WebSockets", "concept", r"websockets?|socket\.io"),
    ("Microservices", "concept", r"microservices?"), ("gRPC", "framework", r"grpc"),
    ("PostgreSQL", "database", r"postgres(?:ql)?|aurora"), ("MySQL", "database", r"mysql"),
    ("MongoDB", "database", r"mongo(?:db)?"), ("Redis", "database", r"redis"), ("DynamoDB", "database", r"dynamodb"),
    ("SQLite", "database", r"sqlite"), ("Elasticsearch", "database", r"elasticsearch|opensearch"),
    ("Cassandra", "database", r"cassandra"), ("Snowflake", "database", r"snowflake"),
    ("Kafka", "data", r"kafka"), ("Airflow", "data", r"airflow"), ("Spark", "data", r"\bspark\b|pyspark"),
    ("Hadoop", "data", r"hadoop|\bhive\b"), ("ETL", "data", r"\betl\b|\belt\b|data pipelines?|data ingestion"),
    ("Athena", "data", r"athena"), ("dbt", "data", r"\bdbt\b"), ("Databricks", "data", r"databricks"),
    ("Pandas", "library", r"pandas"), ("NumPy", "library", r"numpy"), ("PyTorch", "library", r"pytorch"),
    ("TensorFlow", "library", r"tensorflow"), ("scikit-learn", "library", r"scikit[\s-]?learn|sklearn"),
    ("Machine Learning", "concept", r"machine learning|\bml\b|deep learning"),
    ("LLMs", "concept", r"\bllms?\b|large language models?|generative ai|genai|\bgpt\b|\brag\b"),
    ("AWS", "cloud", r"\baws\b|amazon web services|\bec2\b|\bs3\b|\becs\b|lambda"), ("GCP", "cloud", r"\bgcp\b|google cloud"),
    ("Azure", "cloud", r"azure"), ("Docker", "devtool", r"docker|containers?"), ("Kubernetes", "devtool", r"kubernetes|\bk8s\b"),
    ("Terraform", "devtool", r"terraform|infrastructure as code|\biac\b"), ("CI/CD", "devtool", r"ci/?cd|github actions|jenkins|continuous (?:integration|delivery)"),
    ("Git", "devtool", r"\bgit\b|github|gitlab"), ("Linux", "devtool", r"linux|unix"),
    ("Data Structures & Algorithms", "cs", r"data structures?|algorithms?|\bdsa\b"),
    ("System Design", "cs", r"system design|distributed systems?|scalab"), ("Operating Systems", "cs", r"operating systems?"),
    ("Computer Networks", "cs", r"networking|computer networks?|tcp"), ("Databases", "cs", r"\bdbms\b|relational databases?"),
    ("Testing", "concept", r"unit tests?|unit testing|\btdd\b|pytest|jest|integration tests?|test[\s-]driven"),
    ("OAuth / Auth", "concept", r"oauth|\boidc\b|\bsso\b|\bjwt\b|authentication|\brbac\b"),
    ("Observability", "concept", r"observability|prometheus|grafana|datadog|monitoring"),
    ("Concurrency", "cs", r"concurren|multi-?thread|async"),
    ("Low latency", "cs", r"low[\s-]latency|high[\s-]performance"),
    ("OOP", "cs", r"object[\s-]oriented|\boop\b|design patterns"),
    ("Agile", "concept", r"agile|scrum"),
]
TERMS = {name: (cat, re.compile(rf"(?<![\w+#]){pat}(?![\w#]|\+\+)" if name not in ("C++", "C#") else pat,
                                  re.I if name != "Go" else 0)) for name, cat, pat in _TERMS}
CATEGORY = {name: cat for name, (cat, _) in TERMS.items()}


def find_terms(text: str) -> set[str]:
    return {name for name, (_, rx) in TERMS.items() if rx.search(text)}
