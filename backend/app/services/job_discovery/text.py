"""HTML to text and small normalisation helpers."""
import html
import re

from bs4 import BeautifulSoup


def html_to_text(raw: str) -> str:
    if not raw:
        return ""
    # Greenhouse returns entity-escaped HTML; unescape first.
    if "&lt;" in raw and "<" not in raw:
        raw = html.unescape(raw)
    soup = BeautifulSoup(raw, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for br in soup.find_all(["br", "p", "div", "h1", "h2", "h3", "h4"]):
        br.insert_after("\n")
    text = soup.get_text()
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def normalise_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = re.sub(r"[^a-z0-9+#. ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()
