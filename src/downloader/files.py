"""File download helpers: download a resource via Playwright expect_download."""

import logging
import re
import unicodedata
from pathlib import Path

from .selectors import SKIP_PATTERNS

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def download_resource(page, name: str, url: str, dest_dir: Path) -> Path | None:
    """Download a single resource to dest_dir. Returns saved Path or None.

    For /mod/folder/ URLs use download_folder() instead — this only handles
    single-file resources.
    """
    if any(p in url for p in SKIP_PATTERNS):
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Try via page.goto first (most Moodle file resources work this way)
    result = _try_download(page, url, dest_dir, click=False)
    if result:
        return result

    # Fallback: navigate to page and click the download link
    result = _try_download(page, url, dest_dir, click=True)
    if result:
        return result

    return None


def download_folder(page, url: str, dest_dir: Path) -> list[Path]:
    """Download every PDF/DOCX inside a Moodle /mod/folder/ resource.

    Returns list of saved Paths (may be empty).
    """
    saved: list[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        logger.warning(f"No se pudo abrir folder {url}: {e}")
        return saved

    file_hrefs: list[str] = []
    seen: set[str] = set()
    for link in page.query_selector_all("a[href*='/pluginfile.php']"):
        href = link.get_attribute("href") or ""
        if not href or href in seen:
            continue
        seen.add(href)
        file_hrefs.append(href)

    for file_url in file_hrefs:
        try:
            with page.expect_download(timeout=20000) as dl_info:
                page.evaluate("(u) => window.location.href = u", file_url)
            download = dl_info.value
            suggested = download.suggested_filename or "file"
            ext = Path(suggested).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                download.cancel()
                continue
            dest_path = dest_dir / _sanitize_filename(suggested)
            if dest_path.exists():
                logger.info(f"Ya existe: {suggested}")
                download.cancel()
                saved.append(dest_path)
                continue
            download.save_as(str(dest_path))
            logger.info(f"Descargado: {suggested} -> {dest_dir.name}/")
            saved.append(dest_path)
        except Exception as e:
            logger.debug(f"Skip {file_url}: {e}")
            continue

    return saved


def _try_download(page, url: str, dest_dir: Path, click: bool) -> Path | None:
    try:
        with page.expect_download(timeout=20000) as dl_info:
            if click:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                dl_link = page.locator("a[href*='/pluginfile.php']").first
                if dl_link.count() == 0:
                    return None
                dl_link.click()
            else:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)

        download = dl_info.value
        suggested = download.suggested_filename or "file"
        ext = Path(suggested).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            download.cancel()
            return None

        dest_path = dest_dir / _sanitize_filename(suggested)
        if dest_path.exists():
            logger.info(f"Ya existe: {suggested}")
            download.cancel()
            return dest_path  # still count as "available"

        download.save_as(str(dest_path))
        logger.info(f"Descargado: {suggested} -> {dest_dir.name}/")
        return dest_path

    except Exception:
        return None


def _sanitize_filename(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not unicodedata.combining(c))
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip()[:120]


def _sanitize_dirname(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not unicodedata.combining(c))
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:60]
