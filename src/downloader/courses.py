"""Course discovery and matching for Moodle UNO."""

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .selectors import CAMPUS_URL

logger = logging.getLogger(__name__)


def list_courses(page) -> list[tuple[str, str]]:
    """Return list of (course_name, course_url) merged from dashboard + full course list."""
    seen: set[str] = set()
    courses: list[tuple[str, str]] = []

    for name, href in _scrape_course_links(page, f"{CAMPUS_URL}/my/"):
        if href not in seen:
            seen.add(href)
            courses.append((name, href))

    # Follow "Todos los cursos" link from dashboard (UNO Moodle theme).
    extra = _scrape_via_all_courses_link(page)
    for name, href in extra:
        if href not in seen:
            seen.add(href)
            courses.append((name, href))

    if not courses:
        courses = _list_courses_fallback(page)

    if not courses:
        _dump_dashboard_diagnostics(page)

    logger.info(f"list_courses() devolvió {len(courses)} cursos.")
    return courses


def _scrape_via_all_courses_link(page) -> list[tuple[str, str]]:
    """Locate the 'Todos los cursos' anchor on /my/ and follow it."""
    try:
        page.goto(f"{CAMPUS_URL}/my/", wait_until="networkidle", timeout=20000)
    except Exception:
        return []

    target_href: str | None = None
    candidates = (
        "todos los cursos",
        "todos mis cursos",
        "all courses",
        "ver todos",
    )
    try:
        for link in page.query_selector_all("a"):
            text = (link.inner_text() or "").strip().lower()
            if not text:
                continue
            if any(c in text for c in candidates):
                # el.href returns the resolved absolute URL
                target_href = link.evaluate("el => el.href")
                if target_href:
                    break
    except Exception:
        return []

    if not target_href:
        return []

    logger.info(f"Siguiendo link 'Todos los cursos' -> {target_href}")
    return _scrape_course_links(page, target_href)


def _scrape_course_links(page, url: str) -> list[tuple[str, str]]:
    """Navigate to url and pull every (name, href) anchor pointing to a course."""
    try:
        page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception as e:
        logger.warning(f"No se pudo cargar {url}: {e}")
        return []

    try:
        page.wait_for_selector("a[href*='course/view.php']", timeout=10000)
    except Exception:
        pass

    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for link in page.query_selector_all("a[href*='/course/view.php']"):
        href = link.get_attribute("href") or ""
        if "/course/view.php" not in href or href in seen:
            continue

        name = (link.inner_text() or "").strip()
        if not name:
            inner = link.query_selector(".coursename, .multiline, .text-truncate")
            if inner:
                name = (inner.inner_text() or "").strip()
        if not name:
            name = (link.get_attribute("title") or "").strip()
        if not name:
            name = (link.get_attribute("aria-label") or "").strip()

        name = re.sub(r'\s+', ' ', name).strip()
        if not name:
            continue

        seen.add(href)
        out.append((name, href))

    return out


def _dump_dashboard_diagnostics(page) -> None:
    """Save URL/title/screenshot/HTML when course list comes up empty."""
    try:
        url = page.url
    except Exception:
        url = "<unknown>"
    try:
        title = page.title()
    except Exception:
        title = "<unknown>"
    try:
        anchor_count = len(page.query_selector_all("a"))
    except Exception:
        anchor_count = -1

    logger.error(
        "Dashboard sin cursos detectados.\n"
        f"  URL: {url}\n"
        f"  Title: {title}\n"
        f"  Total <a> en página: {anchor_count}"
    )

    debug_dir = Path("./data/debug")
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = debug_dir / "dashboard.png"
        html_path = debug_dir / "dashboard.html"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            logger.warning(f"No se pudo guardar screenshot: {e}")
        try:
            html_path.write_text(page.content(), encoding="utf-8")
        except Exception as e:
            logger.warning(f"No se pudo guardar HTML: {e}")
        logger.info(
            f"Diagnóstica guardada en {debug_dir.resolve()} "
            "(dashboard.png y dashboard.html)."
        )
    except Exception as e:
        logger.warning(f"No se pudo crear carpeta de debug: {e}")


def _list_courses_fallback(page) -> list[tuple[str, str]]:
    try:
        page.goto(f"{CAMPUS_URL}/course/index.php", wait_until="networkidle", timeout=20000)
        seen: set[str] = set()
        courses: list[tuple[str, str]] = []
        for link in page.query_selector_all("a"):
            href = link.get_attribute("href") or ""
            name = (link.inner_text() or "").strip()
            if "/course/view.php" in href and href not in seen and name:
                seen.add(href)
                courses.append((name, href))
        return courses
    except Exception:
        return []


def find_matching_course(
    courses: list[tuple[str, str]],
    subject_name: str,
    year: int,
) -> tuple[str, str] | None:
    """Find the course matching subject_name (and optionally year).

    Course format at UNO: "01017-Álgebra y Geometría Analítica (1C2024)"
    """
    needle = _normalize(subject_name)
    year_str_full = str(year)
    year_str_short = year_str_full[-2:]

    def _course_year(name: str) -> int | None:
        return extract_course_year(name)

    def _matches(name: str, require_year: bool) -> bool:
        norm = _normalize(name)
        if needle not in norm:
            return False
        if not require_year:
            return True
        cy = _course_year(name)
        if cy is not None:
            return cy == year
        return year_str_full in norm or year_str_short in norm

    matches = [(n, u) for n, u in courses if _matches(n, require_year=True)]

    if not matches:
        matches = [(n, u) for n, u in courses if _matches(n, require_year=False)]
        if matches:
            logger.warning(
                f"No se encontró '{subject_name}' para {year}. "
                f"Coincidencia sin año: {[n for n, _ in matches]}"
            )

    if not matches:
        available = [n for n, _ in courses]
        logger.error(
            f"No se encontró ningún curso para '{subject_name}' (año {year}). "
            f"Total cursos detectados: {len(available)}"
        )
        for n in available:
            logger.error(f"  - {n}")
        return None

    if len(matches) > 1:
        logger.warning(
            f"Múltiples coincidencias para '{subject_name}': "
            f"{[n for n, _ in matches]}. Usando el primero."
        )

    return matches[0]


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def current_year() -> int:
    return datetime.now().year


def extract_course_year(name: str) -> int | None:
    """Extract academic year from a course title.

    Matches:
      "01017-Álgebra (1C2024)"   -> 2024  (semester prefix, 4 digits)
      "01017-Álgebra (2C24)"     -> 2024  (semester prefix, 2 digits)
      "07034 - POO II (2026)"    -> 2026  (parenthesized year)
      "Algebra 2026"             -> 2026  (trailing 4-digit year)
    """
    m = re.search(r'\d[Cc](\d{2,4})', name)
    if m:
        raw = m.group(1)
        return (2000 + int(raw)) if len(raw) == 2 else int(raw)

    m = re.search(r'\((\d{4})\)', name)
    if m:
        return int(m.group(1))

    m = re.search(r'\b(20\d{2})\b', name)
    if m:
        return int(m.group(1))

    return None


def parse_subject_query(query: str) -> tuple[str, int | None]:
    """
    Parse an optional trailing year from a subject query string.

    'POO II 2026'      -> ('POO II', 2026)
    'POO II 1C2026'    -> ('POO II', 2026)
    'POO II 2C24'      -> ('POO II', 2024)
    'POO II'           -> ('POO II', None)
    'Algebra y Geom 1' -> ('Algebra y Geom 1', None)
    """
    if not query:
        return query, None
    q = query.strip()
    # semester prefix: 1C2026 / 2C2026 / 1C24 at end
    m = re.search(r'\s+\d[Cc](\d{2,4})\s*$', q)
    if m:
        raw = m.group(1)
        year = (2000 + int(raw)) if len(raw) == 2 else int(raw)
        return q[:m.start()].strip(), year
    # plain 4-digit year at end (19XX or 20XX)
    m = re.search(r'\s+((?:19|20)\d{2})\s*$', q)
    if m:
        return q[:m.start()].strip(), int(m.group(1))
    return q, None
