"""File download helpers: download a resource via Playwright + HTTP session."""

import logging
import re
import unicodedata
from pathlib import Path

from .selectors import SKIP_PATTERNS

logger = logging.getLogger(__name__)

# Whitelist: extensiones que vamos a descargar.
SUPPORTED_EXTENSIONS = {
    # Documentos
    ".pdf", ".docx", ".doc", ".odt", ".rtf",
    # Hojas de cálculo
    ".xlsx", ".xls", ".ods", ".csv",
    # Presentaciones
    ".pptx", ".ppt", ".odp",
    # Comprimidos
    ".zip", ".rar", ".7z", ".tar", ".gz",
    # Texto / código común en cursos
    ".txt", ".md", ".java", ".py", ".js", ".ts", ".c", ".cpp", ".h",
    ".html", ".css", ".sql", ".json", ".xml", ".yaml", ".yml",
    # Imágenes (slides a veces vienen como imagen)
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
}

# Blacklist explícita: ejecutables y scripts. Defensa contra material
# malicioso aunque Moodle lo sirva. NUNCA descargar.
BLOCKED_EXTENSIONS = {
    ".exe", ".msi", ".bat", ".cmd", ".com", ".ps1", ".vbs",
    ".scr", ".dll", ".sh", ".app", ".dmg", ".pkg", ".deb", ".rpm",
    ".jar",  # potencialmente ejecutable
}


def download_resource(page, name: str, url: str, dest_dir: Path) -> Path | None:
    """Download a single resource to dest_dir. Returns saved Path or None.

    Strategy:
      1. Listen for any pluginfile.php response while page.goto() loads —
         catches viewers that fetch the file via JS after DOM-ready.
      2. expect_download() inside the goto for force-download resources.
      3. If neither fires, scan the static DOM for an embed URL.
      4. Last resort: dump page HTML+screenshot to data/debug/ for offline
         inspection so we know what selector to add next.
    """
    if any(p in url for p in SKIP_PATTERNS):
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)

    captured: list[str] = []

    def _capture(resp):
        try:
            if "pluginfile.php" in resp.url:
                captured.append(resp.url)
        except Exception:
            pass

    page.on("response", _capture)
    try:
        # Attempt 1: force-download via expect_download
        try:
            with page.expect_download(timeout=4000) as dl_info:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return _save_download(dl_info.value, dest_dir, name)
        except Exception:
            pass  # no auto-download, page is loaded

        # Let JS-deferred viewers settle so iframe/embed gets its src populated
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass

        # Attempt 2: URL captured from network during page load
        if captured:
            return _fetch_via_request(page, captured[0], dest_dir, name)

        # Attempt 3: scan static DOM
        file_url = _find_pluginfile_url(page)
        if file_url:
            return _fetch_via_request(page, file_url, dest_dir, name)

        _dump_resource_diagnostics(page, name)
        logger.info(f"Sin URL pluginfile: {name}")
        return None
    finally:
        try:
            page.remove_listener("response", _capture)
        except Exception:
            pass


def _fetch_via_request(page, file_url: str, dest_dir: Path, label: str) -> Path | None:
    """Fetch a pluginfile URL via APIRequestContext (uses session cookies).

    Returns saved Path or None. Avoids the browser download dialog entirely.

    Timeout 120s covers PDFs up to ~10 MB on slow Moodle servers (UNO).
    """
    logger.info(f"Descargando: {label} ...")
    try:
        response = page.context.request.get(file_url, timeout=120000)
    except Exception as e:
        logger.warning(f"Request fallido '{label}': {e}")
        return None

    if not response.ok:
        logger.warning(f"HTTP {response.status} en '{label}'")
        return None

    suggested = _suggest_filename(response, file_url) or "file"
    ext = Path(suggested).suffix.lower()

    if ext in BLOCKED_EXTENSIONS:
        logger.warning(f"BLOQUEADO por seguridad: {suggested} ({ext})")
        return None
    if ext not in SUPPORTED_EXTENSIONS:
        logger.info(f"Skip '{label}': extensión {ext or '(ninguna)'} no en whitelist")
        return None

    dest_path = dest_dir / _sanitize_filename(suggested)
    if dest_path.exists():
        logger.info(f"Ya existe: {suggested}")
        return dest_path

    try:
        body = response.body()
        dest_path.write_bytes(body)
    except Exception as e:
        logger.warning(f"No se pudo guardar '{label}': {e}")
        return None

    size_mb = len(body) / 1024 / 1024
    logger.info(f"Descargado: {suggested} ({size_mb:.1f} MB) -> {dest_dir.name}/")
    return dest_path


def _suggest_filename(response, file_url: str) -> str | None:
    """Pull a filename from Content-Disposition first, fall back to URL path.

    Repairs UTF-8-as-Latin-1 mojibake (e.g. 'bÃ¡sicos' -> 'básicos').
    """
    try:
        disp = response.headers.get("content-disposition", "")
    except Exception:
        disp = ""

    name: str | None = None
    m = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disp, flags=re.IGNORECASE)
    if m:
        from urllib.parse import unquote
        name = unquote(m.group(1)).strip().strip('"')

    if not name:
        from urllib.parse import urlparse, unquote
        path = urlparse(file_url).path
        if path:
            name = unquote(path.rsplit("/", 1)[-1])

    if name:
        name = _fix_mojibake(name)
    return name


def _fix_mojibake(s: str) -> str:
    """Repair UTF-8 bytes that were decoded as Latin-1.

    Heuristic: presence of Ã/Â/â followed by other non-ASCII chars is a
    strong signal of mojibake. encode('latin-1').decode('utf-8') reverses it.
    """
    if not any(ch in s for ch in "ÃÂâ"):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _find_pluginfile_url(page) -> str | None:
    """Look for a Moodle pluginfile.php URL in common embed locations."""
    selectors = [
        ("a",      "href"),
        ("iframe", "src"),
        ("embed",  "src"),
        ("object", "data"),
    ]
    for tag, attr in selectors:
        for el in page.query_selector_all(tag):
            val = el.get_attribute(attr) or ""
            if "pluginfile.php" in val:
                return val
    return None


def _dump_resource_diagnostics(page, label: str) -> None:
    """Save HTML + screenshot of a resource page when no pluginfile URL found.

    Helps offline debugging: open the saved HTML and find where the download
    link actually lives so we can add the right selector in the next round.
    """
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '_', label)[:60] or "unknown"
    debug_dir = Path("./data/debug")
    try:
        debug_dir.mkdir(parents=True, exist_ok=True)
        try:
            page.screenshot(path=str(debug_dir / f"resource-{safe}.png"), full_page=True)
        except Exception:
            pass
        try:
            (debug_dir / f"resource-{safe}.html").write_text(
                page.content(), encoding="utf-8"
            )
        except Exception:
            pass
        logger.info(f"  Diagnóstica: data/debug/resource-{safe}.html")
    except Exception as e:
        logger.debug(f"No se pudo crear data/debug: {e}")


def _save_download(download, dest_dir: Path, label: str) -> Path | None:
    """Save a Playwright Download object honoring whitelist/blacklist."""
    suggested = download.suggested_filename or "file"
    suggested = _fix_mojibake(suggested)
    ext = Path(suggested).suffix.lower()

    if ext in BLOCKED_EXTENSIONS:
        download.cancel()
        logger.warning(f"BLOQUEADO por seguridad: {suggested} ({ext})")
        return None
    if ext not in SUPPORTED_EXTENSIONS:
        download.cancel()
        logger.info(f"Skip '{label}': extensión {ext or '(ninguna)'} no en whitelist")
        return None

    dest_path = dest_dir / _sanitize_filename(suggested)
    if dest_path.exists():
        logger.info(f"Ya existe: {suggested}")
        download.cancel()
        return dest_path

    download.save_as(str(dest_path))
    logger.info(f"Descargado: {suggested} -> {dest_dir.name}/")
    return dest_path


def download_folder(page, url: str, dest_dir: Path) -> list[Path]:
    """Download every supported file inside a Moodle /mod/folder/ resource."""
    saved: list[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        logger.warning(f"No se pudo abrir folder {url}: {e}")
        return saved

    # Some folders lazy-load contents
    try:
        page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass

    file_hrefs: list[str] = []
    seen: set[str] = set()
    for link in page.query_selector_all("a[href*='/pluginfile.php']"):
        href = link.get_attribute("href") or ""
        if not href or href in seen:
            continue
        seen.add(href)
        file_hrefs.append(href)

    logger.info(f"  Folder: {len(file_hrefs)} archivo(s)")
    for file_url in file_hrefs:
        saved_path = _fetch_via_request(page, file_url, dest_dir, file_url)
        if saved_path:
            saved.append(saved_path)

    return saved


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
