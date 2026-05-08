"""Playwright browser launch and Moodle login."""

import logging
import os
from contextlib import contextmanager

from .selectors import LOGIN_URL

logger = logging.getLogger(__name__)


@contextmanager
def launch_browser(headless: bool = True):
    """Context manager: yields (browser, page) with downloads enabled."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright no instalado.\n"
            "Ejecutá: pip install playwright && playwright install chromium"
        )
        raise

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            yield browser, page
        finally:
            browser.close()


def login(page, username: str, password: str) -> bool:
    """Log in to Moodle. Returns True on success."""
    logger.info("Iniciando sesión en el campus...")
    try:
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)

        # Try submit button selectors in order
        for sel in ["#loginbtn", "input[type=submit]", "button[type=submit]"]:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.click()
                break

        page.wait_for_load_state("networkidle", timeout=15000)

        if "login" in page.url:
            logger.error("Login fallido. Verificá usuario y contraseña en .env")
            return False

        logger.info("Login exitoso")
        return True

    except Exception as e:
        logger.error(f"Error al hacer login: {e}")
        return False


def get_credentials(
    username: str | None = None,
    password: str | None = None,
) -> tuple[str, str]:
    """Resolve credentials: params > env vars."""
    u = username or os.environ.get("CAMPUS_USER", "")
    p = password or os.environ.get("CAMPUS_PASS", "")
    if not u or not p:
        logger.error(
            "Credenciales del campus no configuradas.\n"
            "Definí CAMPUS_USER y CAMPUS_PASS en .env"
        )
    return u, p
