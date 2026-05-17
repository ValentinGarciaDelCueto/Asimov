"""Resource link discovery and timestamp extraction within a Moodle course page."""

import logging
import re
from datetime import datetime

from .selectors import SKIP_PATTERNS

logger = logging.getLogger(__name__)

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def find_resource_links(page) -> list[tuple[str, str]]:
    """Return (name, url) for every /mod/* activity link on the course page.

    Uses a URL-based catch-all so it works across Moodle 3.x and 4.x themes
    without relying on CSS class names that change between versions.
    """
    seen: set[str] = set()
    links: list[tuple[str, str]] = []

    for link in page.query_selector_all("a[href*='/mod/']"):
        href = link.get_attribute("href") or ""
        if not href or href in seen:
            continue

        # Pick a human-readable name from typical containers, then fall back.
        name = ""
        for sel in [".instancename", ".activityname", ".multiline"]:
            el = link.query_selector(sel)
            if el:
                name = (el.inner_text() or "").strip()
                if name:
                    break
        if not name:
            name = (link.inner_text() or "").strip()
        if not name:
            name = (link.get_attribute("aria-label") or "").strip()
        if not name:
            name = href.rsplit("/", 1)[-1]

        name = re.sub(r'\s+', ' ', name).strip()
        seen.add(href)
        links.append((name, href))

    return links


def filter_file_links(links: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Keep only links that are downloadable files or folders of files."""
    keep = ("/mod/resource/", "/mod/folder/")
    file_links = [
        (n, u) for n, u in links
        if not any(p in u for p in SKIP_PATTERNS)
        and any(k in u for k in keep)
    ]
    if not file_links:
        file_links = [
            (n, u) for n, u in links
            if not any(p in u for p in SKIP_PATTERNS)
        ]
    return file_links


def get_resource_timestamp(page, resource_url: str) -> datetime | None:
    """Navigate to resource page and extract last-modified timestamp."""
    try:
        page.goto(resource_url, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        return None

    time_el = page.query_selector("time[datetime]")
    if time_el:
        dt_str = time_el.get_attribute("datetime")
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            pass

    for sel in [".resourcelastmodified", ".modified", ".filedetails dd", ".resourceworkaround"]:
        el = page.query_selector(sel)
        if el:
            parsed = _parse_spanish_date(el.inner_text())
            if parsed:
                return parsed

    try:
        return _parse_spanish_date(page.inner_text("body"))
    except Exception:
        return None


def pick_latest_resource(page, resource_links: list[tuple[str, str]]) -> tuple[str, str]:
    """Return the most recently modified resource, or last in list if no timestamps."""
    best_name, best_url, best_ts = None, None, None

    for name, url in resource_links:
        ts = get_resource_timestamp(page, url)
        if ts is not None:
            if best_ts is None or ts > best_ts:
                best_name, best_url, best_ts = name, url, ts

    if best_url is not None:
        logger.info(f"Timestamp más reciente: {best_ts}")
        return best_name, best_url

    logger.info("Sin timestamps, usando el último recurso de la página.")
    return resource_links[-1]


def _parse_spanish_date(text: str) -> datetime | None:
    pattern = r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})(?:[,\s]+(\d{1,2}):(\d{2}))?"
    m = re.search(pattern, text.lower())
    if not m:
        return None
    day = int(m.group(1))
    month = _MONTHS_ES.get(m.group(2))
    if not month:
        return None
    year = int(m.group(3))
    hour = int(m.group(4)) if m.group(4) else 0
    minute = int(m.group(5)) if m.group(5) else 0
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None
