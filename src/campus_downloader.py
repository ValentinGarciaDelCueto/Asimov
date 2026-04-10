# ============================================================
#  campus_downloader.py — Descarga automática desde Moodle UNO
#  Usa Playwright para navegar el campus como si fueras vos
# ============================================================

import logging
import time
import re
import os
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# URL base del campus
CAMPUS_URL = "http://campusvirtual.uno.edu.ar/moodle"
LOGIN_URL  = f"{CAMPUS_URL}/login/index.php"


# ── Entrada pública ──────────────────────────────────────────

def download_new_materials(download_root: Path) -> int:
    """
    Se loguea al campus, recorre todos los cursos y descarga
    PDFs y DOCX nuevos en download_root/<Nombre Materia>/

    Retorna la cantidad de archivos descargados.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright no instalado.\n"
            "Ejecutá en CMD:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
        return 0

    username, password = _get_credentials()
    if not username or not password:
        return 0

    downloaded = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=False para ver el navegador
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            # 1. Login
            if not _login(page, username, password):
                return 0

            # 2. Obtener lista de cursos del usuario
            courses = _get_courses(page)
            logger.info(f"Cursos encontrados: {len(courses)}")

            # 3. Por cada curso, descargar materiales
            for course_name, course_url in courses:
                logger.info(f"\n📘 Procesando: {course_name}")
                course_dir = download_root / _sanitize_dirname(course_name)
                course_dir.mkdir(parents=True, exist_ok=True)

                count = _download_course_files(page, course_url, course_dir)
                downloaded += count
                logger.info(f"  → {count} archivo(s) descargado(s)")

        except Exception as e:
            logger.error(f"Error durante la descarga: {e}", exc_info=True)
        finally:
            browser.close()

    logger.info(f"\n✅ Total descargado: {downloaded} archivo(s)")
    return downloaded


def download_latest_for_subject(
    subject_name: str,
    dest_folder: str | Path,
    year: int | None = None,
    username: str | None = None,
    password: str | None = None,
) -> "Path | None":
    """
    Busca el curso que coincida con subject_name (y opcionalmente year),
    determina el archivo más reciente y lo descarga en dest_folder.

    Retorna el Path al archivo descargado, o None si no encontró nada.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright no instalado.\n"
            "Ejecutá en CMD:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
        return None

    if year is None:
        year = datetime.now().year

    # Credenciales: params > env vars
    if not username or not password:
        env_user, env_pass = _get_credentials()
        username = username or env_user
        password = password or env_pass
    if not username or not password:
        return None

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            if not _login(page, username, password):
                return None

            courses = _get_courses(page)
            if not courses:
                logger.warning("No se encontraron cursos.")
                return None

            match = _find_matching_course(courses, subject_name, year)
            if not match:
                available = [n for n, _ in courses]
                logger.error(
                    f"No se encontró ningún curso que coincida con "
                    f"'{subject_name}' (año {year}).\n"
                    f"Cursos disponibles: {available}"
                )
                return None

            course_name, course_url = match
            logger.info(f"Curso encontrado: {course_name}")

            page.goto(course_url, wait_until="networkidle", timeout=20000)
            time.sleep(1)
            resource_links = _find_resource_links(page)

            # Filtrar solo módulos de archivo reales
            skip_patterns = ["/forum/", "/quiz/", "/assign/", "/page/", "/url/",
                             "/chat/", "/choice/", "/survey/", "/wiki/", "/lesson/"]
            file_links = [
                (n, u) for n, u in resource_links
                if not any(p in u for p in skip_patterns)
                and "/mod/resource/" in u
            ]

            # Fallback: si no hay /mod/resource/, usar todos los que no sean skip
            if not file_links:
                file_links = [
                    (n, u) for n, u in resource_links
                    if not any(p in u for p in skip_patterns)
                ]

            if not file_links:
                logger.warning(f"No se encontraron recursos descargables en '{course_name}'.")
                return None

            chosen_name, chosen_url = _pick_latest_resource(page, file_links)
            logger.info(f"Recurso más reciente: {chosen_name}")

            result_path = _download_single_resource(page, chosen_name, chosen_url, dest_folder)
            return result_path

        except Exception as e:
            logger.error(f"Error en download_latest_for_subject: {e}", exc_info=True)
            return None
        finally:
            browser.close()


# ── Login ────────────────────────────────────────────────────

def _login(page, username: str, password: str) -> bool:
    """Inicia sesión en Moodle."""
    logger.info("Iniciando sesión en el campus...")
    try:
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('input[type="submit"]')

        page.wait_for_load_state("networkidle", timeout=15000)

        # Verificar login exitoso: Moodle redirige al dashboard
        if "login" in page.url:
            logger.error("❌ Login fallido. Verificá usuario y contraseña en .env")
            return False

        logger.info("✅ Login exitoso")
        return True

    except Exception as e:
        logger.error(f"Error al hacer login: {e}")
        return False


# ── Obtener cursos ───────────────────────────────────────────

def _get_courses(page) -> list[tuple[str, str]]:
    """
    Extrae los cursos del usuario desde el dashboard de Moodle.
    Retorna lista de (nombre_curso, url_curso).
    """
    try:
        page.goto(f"{CAMPUS_URL}/my/", wait_until="networkidle", timeout=20000)

        # Moodle lista los cursos con este selector estándar
        course_links = page.query_selector_all(
            "a.coursename, "
            ".course-info-container a, "
            "[data-region='course-content'] a, "
            ".coursebox .coursename a, "
            "h3.coursename a"
        )

        seen = set()
        courses = []
        for link in course_links:
            href = link.get_attribute("href") or ""
            name = (link.inner_text() or "").strip()

            # Solo URLs de cursos válidos
            if "/course/view.php" in href and href not in seen and name:
                seen.add(href)
                courses.append((name, href))

        # Fallback: si no encontró cursos, intenta desde "Mis cursos"
        if not courses:
            courses = _get_courses_fallback(page)

        return courses

    except Exception as e:
        logger.error(f"Error al obtener cursos: {e}")
        return []


def _get_courses_fallback(page) -> list[tuple[str, str]]:
    """Método alternativo para obtener cursos desde el menú de navegación."""
    try:
        page.goto(f"{CAMPUS_URL}/course/index.php", wait_until="networkidle", timeout=20000)
        links = page.query_selector_all("a")
        courses = []
        seen = set()
        for link in links:
            href = link.get_attribute("href") or ""
            name = (link.inner_text() or "").strip()
            if "/course/view.php" in href and href not in seen and name:
                seen.add(href)
                courses.append((name, href))
        return courses
    except Exception:
        return []


def _find_matching_course(
    courses: list,
    subject_name: str,
    year: int,
) -> "tuple[str, str] | None":
    """
    Busca en la lista de cursos el que coincida con subject_name y year.
    Formato típico UNO: "01017-Álgebra y Geometría Analítica (1C2024)"
    El año puede aparecer como 1C2024, 2C2024, 1C26, etc.
    """
    needle = _normalize(subject_name)
    year_str_full = str(year)          # "2026"
    year_str_short = year_str_full[-2:]  # "26"

    def _course_year(course_name: str) -> "int | None":
        """Extrae el año numérico de un nombre de curso (ej. 1C2024 → 2024)."""
        m = re.search(r'\d[Cc](\d{2,4})', course_name)
        if not m:
            return None
        raw = m.group(1)
        if len(raw) == 2:
            return 2000 + int(raw)
        return int(raw)

    def _matches(course_name: str, require_year: bool) -> bool:
        norm = _normalize(course_name)
        if needle not in norm:
            return False
        if not require_year:
            return True
        cy = _course_year(course_name)
        if cy is not None:
            return cy == year
        # Si no hay patrón cuatrimestral, buscar el año como texto directo
        return year_str_full in norm or year_str_short in norm

    # Primer intento: con año
    matches = [(n, u) for n, u in courses if _matches(n, require_year=True)]

    # Fallback: sin año
    if not matches:
        matches = [(n, u) for n, u in courses if _matches(n, require_year=False)]
        if matches:
            logger.warning(
                f"No se encontró '{subject_name}' para el año {year}. "
                f"Usando coincidencia sin año: {[n for n, _ in matches]}"
            )

    if not matches:
        return None

    if len(matches) > 1:
        logger.warning(
            f"Múltiples cursos coinciden con '{subject_name}': "
            f"{[n for n, _ in matches]}. Usando el primero."
        )

    return matches[0]


# ── Descargar archivos de un curso ───────────────────────────

def _download_course_files(page, course_url: str, dest_dir: Path) -> int:
    """
    Entra al curso y descarga todos los PDF y DOCX que encuentra.
    Maneja recursos directos y también módulos de carpeta/zip.
    """
    try:
        page.goto(course_url, wait_until="networkidle", timeout=20000)
        time.sleep(1)

        # Buscar todos los links de recursos en la página del curso
        resource_links = _find_resource_links(page)
        logger.info(f"  Recursos encontrados: {len(resource_links)}")

        downloaded = 0
        for res_name, res_url in resource_links:
            result = _download_resource(page, res_name, res_url, dest_dir)
            downloaded += result

        return downloaded

    except Exception as e:
        logger.error(f"  Error procesando curso: {e}")
        return 0


def _find_resource_links(page) -> list[tuple[str, str]]:
    """Encuentra todos los links de recursos (PDF, DOCX, carpetas) en la página del curso."""
    links = []
    seen = set()

    # Selector estándar de Moodle para actividades/recursos
    elements = page.query_selector_all(
        ".activityinstance a, "
        ".activity a.aalink, "
        "[data-activityname] a, "
        ".instancename"
    )

    for el in elements:
        # Subir al padre para obtener el link real si el elemento es solo el nombre
        href = el.get_attribute("href")
        if not href:
            parent = el.query_selector("xpath=..")
            if parent:
                href = parent.get_attribute("href")

        name_el = el.query_selector(".instancename") or el
        name = (name_el.inner_text() or href or "recurso").strip()
        name = re.sub(r'\s+', ' ', name)

        if href and href not in seen:
            seen.add(href)
            links.append((name, href))

    return links


def _download_resource(page, name: str, url: str, dest_dir: Path) -> int:
    """
    Intenta descargar un recurso. Maneja:
    - Recursos directos (PDF/DOCX embebidos en Moodle)
    - Links directos a archivos
    Retorna 1 si descargó algo, 0 si no.
    """
    # Filtrar URLs claramente no descargables
    skip_patterns = ["/forum/", "/quiz/", "/assign/", "/page/", "/url/",
                     "/chat/", "/choice/", "/survey/", "/wiki/", "/lesson/"]
    if any(p in url for p in skip_patterns):
        return 0

    try:
        # Navegar al recurso y capturar la descarga
        with page.expect_download(timeout=20000) as download_info:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

        download = download_info.value
        suggested = download.suggested_filename or name

        # Solo procesar PDF y DOCX
        ext = Path(suggested).suffix.lower()
        if ext not in [".pdf", ".docx"]:
            download.cancel()
            return 0

        # Verificar si ya existe
        dest_path = dest_dir / _sanitize_filename(suggested)
        if dest_path.exists():
            logger.info(f"    ⏭️  Ya existe: {suggested}")
            return 0

        download.save_as(str(dest_path))
        logger.info(f"    ⬇️  Descargado: {suggested}")
        return 1

    except Exception:
        # Muchos links no generan descarga (son páginas normales), eso es esperado
        return 0


def _download_single_resource(page, name: str, url: str, dest_dir: Path) -> "Path | None":
    """
    Como _download_resource pero retorna el Path del archivo descargado,
    o None si no se pudo descargar. Sobreescribe si ya existe.
    """
    skip_patterns = ["/forum/", "/quiz/", "/assign/", "/page/", "/url/",
                     "/chat/", "/choice/", "/survey/", "/wiki/", "/lesson/"]
    if any(p in url for p in skip_patterns):
        return None

    try:
        with page.expect_download(timeout=20000) as download_info:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

        download = download_info.value
        suggested = download.suggested_filename or name
        ext = Path(suggested).suffix.lower()
        if ext not in [".pdf", ".docx"]:
            download.cancel()
            return None

        dest_path = dest_dir / _sanitize_filename(suggested)
        download.save_as(str(dest_path))
        logger.info(f"    ⬇️  Descargado: {suggested}")
        return dest_path

    except Exception:
        return None


_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_spanish_date(text: str) -> "datetime | None":
    """
    Parsea fechas en formato Moodle español:
      "martes, 15 de enero de 2026, 10:30"  →  datetime(2026, 1, 15, 10, 30)
    """
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


def _get_resource_timestamp(page, resource_url: str) -> "datetime | None":
    """
    Navega a la página del recurso Moodle y extrae el timestamp de
    última modificación. Retorna None si no lo encuentra.
    """
    try:
        page.goto(resource_url, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        return None

    # Estrategia 1: <time datetime="..."> (ISO 8601, más confiable)
    time_el = page.query_selector("time[datetime]")
    if time_el:
        dt_str = time_el.get_attribute("datetime")
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            pass

    # Estrategia 2: selectores CSS comunes de Moodle
    for sel in [".resourcelastmodified", ".modified", ".filedetails dd", ".resourceworkaround"]:
        el = page.query_selector(sel)
        if el:
            parsed = _parse_spanish_date(el.inner_text())
            if parsed:
                return parsed

    # Estrategia 3: escanear todo el body
    try:
        body_text = page.inner_text("body")
        return _parse_spanish_date(body_text)
    except Exception:
        return None


def _pick_latest_resource(page, resource_links: list) -> tuple:
    """
    Determina el recurso más reciente de la lista.
    - Si al menos uno tiene timestamp, retorna el de mayor fecha.
    - Si ninguno tiene timestamp, retorna el último de la lista
      (en Moodle el orden es cronológico ascendente).
    """
    best_name, best_url, best_ts = None, None, None

    for name, url in resource_links:
        ts = _get_resource_timestamp(page, url)
        if ts is not None:
            if best_ts is None or ts > best_ts:
                best_name, best_url, best_ts = name, url, ts

    if best_url is not None:
        logger.info(f"  Timestamp más reciente: {best_ts}")
        return best_name, best_url

    # Fallback: el último en la lista de la página
    logger.info("  No se encontraron timestamps, usando el último recurso de la página.")
    return resource_links[-1]


# ── Credenciales ─────────────────────────────────────────────

def _get_credentials() -> tuple[str, str]:
    """
    Lee las credenciales del campus desde variables de entorno.
    Nunca hardcodear usuario/contraseña en el código.
    """
    username = os.environ.get("CAMPUS_USER", "")
    password = os.environ.get("CAMPUS_PASS", "")

    if not username or not password:
        logger.error(
            "Credenciales del campus no configuradas.\n"
            "Ejecutá en CMD antes de correr el script:\n"
            "  set CAMPUS_USER=tu_usuario\n"
            "  set CAMPUS_PASS=tu_contraseña\n"
            "O agregalas como variables de entorno permanentes en Windows."
        )
        return "", ""

    return username, password


# ── Utilidades ───────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Minúsculas + quita acentos, para comparaciones tolerantes."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _sanitize_dirname(name: str) -> str:
    """Limpia el nombre del curso para usarlo como carpeta."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:60]


def _sanitize_filename(name: str) -> str:
    """Limpia el nombre de archivo."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip()[:120]


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(
        description="Descarga el archivo más reciente de una materia del campus UNO."
    )
    parser.add_argument(
        "--materia", required=True,
        help='Nombre de la materia, ej: "Problemática Regional"'
    )
    parser.add_argument(
        "--año", dest="anio", type=int, default=None,
        help="Año del curso (por defecto: año actual)"
    )
    parser.add_argument(
        "--dest", required=True,
        help=r'Carpeta destino, ej: "C:\Descargas"'
    )
    parser.add_argument(
        "--usuario", default=None,
        help="Usuario del campus (opcional, por defecto usa CAMPUS_USER)"
    )
    parser.add_argument(
        "--clave", default=None,
        help="Contraseña del campus (opcional, por defecto usa CAMPUS_PASS)"
    )

    args = parser.parse_args()

    result = download_latest_for_subject(
        subject_name=args.materia,
        dest_folder=args.dest,
        year=args.anio,
        username=args.usuario,
        password=args.clave,
    )

    if result:
        print(f"\nArchivo descargado: {result}")
        sys.exit(0)
    else:
        print("\nNo se pudo descargar ningún archivo.", file=sys.stderr)
        sys.exit(1)
