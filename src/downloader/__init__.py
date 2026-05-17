"""Moodle downloader — public API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .browser import get_credentials, launch_browser, login
from .courses import (
    current_year,
    extract_course_year,
    find_matching_course,
    list_courses,
    parse_subject_query,
)
from .files import _sanitize_dirname, download_folder, download_resource
from .resources import filter_file_links, find_resource_links

logger = logging.getLogger(__name__)


@dataclass
class DownloadReport:
    subjects_seen: list[str] = field(default_factory=list)
    files_downloaded: list[Path] = field(default_factory=list)
    files_skipped: list[Path] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


def download(
    raw_root: Path,
    subject_filter: str | None = None,
    year: int | None = None,
    username: str | None = None,
    password: str | None = None,
    headless: bool = True,
    on_event: Callable[[str], None] | None = None,
) -> DownloadReport:
    """
    Log in to Moodle, iterate courses (optionally filtered by subject_filter),
    download PDFs/DOCX into raw_root/{subject}/.

    Returns a DownloadReport with what was downloaded, skipped, and any errors.
    """

    def _emit(msg: str) -> None:
        logger.info(msg)
        if on_event:
            on_event(msg)

    report = DownloadReport()
    raw_root.mkdir(parents=True, exist_ok=True)

    u, p = get_credentials(username, password)
    if not u or not p:
        report.errors.append(("credentials", "CAMPUS_USER / CAMPUS_PASS no configurados"))
        return report

    try:
        with launch_browser(headless=headless) as (_, page):
            if not login(page, u, p):
                report.errors.append(("login", "Login fallido"))
                return report

            courses = list_courses(page)
            _emit(f"Cursos encontrados: {len(courses)}")

            explicit_year = year  # year passed in (or None)

            if subject_filter:
                parsed_subject, parsed_year = parse_subject_query(subject_filter)
                effective_year = explicit_year if explicit_year is not None else parsed_year

                from .courses import _normalize
                needle = _normalize(parsed_subject)
                courses_to_process = [
                    (n, url) for n, url in courses
                    if needle in _normalize(n)
                ]
                if effective_year is not None:
                    courses_to_process = [
                        (n, url) for n, url in courses_to_process
                        if extract_course_year(n) == effective_year
                    ]

                if not courses_to_process:
                    available = [n for n, _ in courses]
                    _emit(
                        f"Sin coincidencias para '{parsed_subject}'"
                        + (f" año {effective_year}" if effective_year else "")
                        + f". Total cursos: {len(available)}"
                    )
                    for n in available:
                        _emit(f"  - {n}")
                else:
                    _emit(f"Coincidencias ({len(courses_to_process)}):")
                    for n, _ in courses_to_process:
                        _emit(f"  - {n}")
            elif explicit_year is not None:
                courses_to_process = [
                    (n, url) for n, url in courses
                    if extract_course_year(n) == explicit_year
                ]
                if not courses_to_process:
                    available = [n for n, _ in courses]
                    _emit(
                        f"Ningún curso del año {explicit_year}. "
                        f"Cursos disponibles: {available}"
                    )
            else:
                courses_to_process = courses

            if not courses_to_process:
                if subject_filter:
                    _emit(f"No se encontraron cursos para '{subject_filter}'")
                return report

            for course_name, course_url in courses_to_process:
                if not course_name:
                    continue
                report.subjects_seen.append(course_name)
                dest_dir = raw_root / _sanitize_dirname(course_name)
                dest_dir.mkdir(parents=True, exist_ok=True)
                _emit(f"Procesando: {course_name}")

                try:
                    page.goto(course_url, wait_until="networkidle", timeout=20000)
                    resource_links = find_resource_links(page)
                    file_links = filter_file_links(resource_links)
                    _emit(f"  Recursos descargables: {len(file_links)}")

                    for res_name, res_url in file_links:
                        if "/mod/folder/" in res_url:
                            results = download_folder(page, res_url, dest_dir)
                        else:
                            single = download_resource(page, res_name, res_url, dest_dir)
                            results = [single] if single else []

                        for result in results:
                            if result.stat().st_mtime > (datetime.now().timestamp() - 5):
                                report.files_downloaded.append(result)
                            else:
                                report.files_skipped.append(result)

                except Exception as e:
                    msg = f"Error procesando {course_name}: {e}"
                    logger.error(msg)
                    report.errors.append((course_name, str(e)))

    except Exception as e:
        logger.error(f"Error fatal en downloader: {e}", exc_info=True)
        report.errors.append(("fatal", str(e)))

    _emit(
        f"Descarga completa: {len(report.files_downloaded)} nuevos, "
        f"{len(report.files_skipped)} existentes, "
        f"{len(report.errors)} errores"
    )
    _emit(f"Archivos guardados en: {raw_root.resolve()}")
    _emit("Próximo: [2] Organizar -> [3] Procesar para subir resúmenes a Drive.")
    return report
