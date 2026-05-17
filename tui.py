# ============================================================
#  tui.py — Interfaz TUI para Asimov (UNO)
#
#  LANZAMIENTO:
#    python tui.py
#
#  TECLAS:
#    S        Guardar configuración del panel activo
#    Q        Salir
#    ?        Ayuda
#    ↑ / ↓   Navegar entre secciones
# ============================================================

from __future__ import annotations

import asyncio
import importlib
import logging
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RadioButton,
    RadioSet,
    RichLog,
    Select,
    Static,
    Switch,
    TextArea,
)
from textual.validation import Number

import config as _config_module

# ── Constantes de modelos ────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

ANTHROPIC_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
]

MODEL_INFO: dict[str, dict] = {
    "llama-3.3-70b-versatile": {
        "provider": "Groq", "tipo": "Gratis", "req_min": 30,
        "tok_min": "6,000", "tok_dia": "100,000", "costo": "—",
        "nota": "Más potente de Groq",
    },
    "llama-3.1-8b-instant": {
        "provider": "Groq", "tipo": "Gratis", "req_min": 30,
        "tok_min": "20,000", "tok_dia": "500,000", "costo": "—",
        "nota": "Más rápido, menor calidad",
    },
    "gemma2-9b-it": {
        "provider": "Groq", "tipo": "Gratis", "req_min": 30,
        "tok_min": "15,000", "tok_dia": "250,000", "costo": "—",
        "nota": "Buen balance velocidad/calidad",
    },
    "mixtral-8x7b-32768": {
        "provider": "Groq", "tipo": "Gratis", "req_min": 30,
        "tok_min": "5,000", "tok_dia": "100,000", "costo": "—",
        "nota": "Contexto grande (32k)",
    },
    "claude-haiku-4-5-20251001": {
        "provider": "Anthropic", "tipo": "Pago", "req_min": "—",
        "tok_min": "—", "tok_dia": "Sin límite", "costo": "$0.25/M tok entrada",
        "nota": "Rápido y económico",
    },
    "claude-sonnet-4-6": {
        "provider": "Anthropic", "tipo": "Pago", "req_min": "—",
        "tok_min": "—", "tok_dia": "Sin límite", "costo": "$3.00/M tok entrada",
        "nota": "Balance calidad/costo",
    },
    "claude-opus-4-7": {
        "provider": "Anthropic", "tipo": "Pago", "req_min": "—",
        "tok_min": "—", "tok_dia": "Sin límite", "costo": "$15.00/M tok entrada",
        "nota": "El más potente",
    },
}

_DEFAULT_PROMPT = _config_module.SUMMARY_PROMPT_TEMPLATE
DOTENV_PATH = Path(__file__).parent / ".env"


# ── Helpers de configuración ─────────────────────────────────

def save_to_env(key: str, value: str) -> None:
    try:
        from dotenv import set_key
        set_key(str(DOTENV_PATH), key, value, quote_mode="never")
    except ImportError:
        pass


def reload_config() -> None:
    """Reload config + ALL src.* modules so saved credentials take effect immediately."""
    try:
        from dotenv import load_dotenv
        load_dotenv(DOTENV_PATH, override=True)
    except ImportError:
        pass

    for name in list(sys.modules):
        if name == "config" or name == "main" or name.startswith("src."):
            try:
                importlib.reload(sys.modules[name])
            except Exception as e:
                logging.debug(f"reload {name} skipped: {e}")


def count_pending_files() -> int:
    try:
        from src.tracker import load_processed, is_processed
        processed = load_processed(_config_module.PROCESSED_LOG)
        root = _config_module.PROCESSED_ROOT
        if not root.exists():
            return 0
        return sum(
            1 for p in root.rglob("*")
            if p.suffix.lower() in _config_module.SUPPORTED_EXTENSIONS
            and not is_processed(p, processed)
        )
    except Exception:
        return 0


# ── CSS ──────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: $surface;
}

Header {
    background: $primary-darken-2;
}

#main-layout {
    height: 1fr;
}

#sidebar {
    width: 22;
    border-right: solid $primary-darken-3;
    background: $surface-darken-1;
    padding: 1 0;
}

#sidebar ListItem {
    padding: 0 2;
}

#sidebar ListItem Label {
    color: $text-muted;
}

#sidebar ListItem.--highlight Label {
    color: $text;
    text-style: bold;
}

#content-area {
    width: 1fr;
    height: 1fr;
}

EstadoPanel, CarpetasPanel, ProveedorPanel, ModeloPanel,
KeysPanel, DrivePanel, PromptPanel, EjecutarPanel {
    height: 1fr;
    padding: 1 2;
    overflow-y: auto;
}

.section-title {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}

.subsection-label {
    text-style: bold;
    color: $text-muted;
    margin-top: 1;
    margin-bottom: 0;
}

.help-text {
    color: $text-muted;
    margin-bottom: 1;
}

.field-row {
    height: auto;
    margin-bottom: 1;
    align-vertical: middle;
}

.field-label {
    width: 28;
    color: $text-muted;
    padding-top: 1;
}

.save-bar {
    height: auto;
    margin-top: 2;
    align-horizontal: right;
}

.save-bar Button {
    margin-left: 1;
}

.stat-box {
    border: solid $primary-darken-2;
    padding: 1 2;
    margin-bottom: 1;
    height: auto;
    background: $surface-darken-1;
}

#stat-log, #run-log {
    height: 12;
    border: solid $primary-darken-2;
    margin-top: 1;
    background: $surface-darken-2;
}

#prompt-textarea {
    height: 22;
    border: solid $primary-darken-2;
    margin-top: 1;
}

#model-info-box {
    border: solid $accent-darken-2;
    padding: 1 2;
    margin-top: 1;
    height: auto;
    background: $surface-darken-1;
}

.exec-row {
    height: auto;
    margin-top: 1;
}

.exec-row Button {
    margin-right: 1;
}

#help-dialog {
    border: solid $accent;
    padding: 2 4;
    background: $surface;
    width: 60;
    height: auto;
    margin: 4 0;
}

#help-dialog Label {
    margin-bottom: 1;
}

.help-key {
    width: 18;
    text-style: bold;
    color: $accent;
}
"""


# ── Paneles ───────────────────────────────────────────────────

class EstadoPanel(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Estado del sistema", classes="section-title")

        with Vertical(classes="stat-box"):
            yield Static("", id="stat-provider")
            yield Static("", id="stat-quota")
            yield Static("", id="stat-pending")
            yield Static("", id="stat-paths")

        yield Label("Últimas líneas del log:", classes="subsection-label")
        yield RichLog(id="stat-log", highlight=True, markup=True, max_lines=30)

        with Horizontal(classes="save-bar"):
            yield Button("Actualizar", variant="default", id="btn-refresh-estado")

    def on_mount(self) -> None:
        self.refresh_stats()

    def refresh_stats(self) -> None:
        import config
        from src.ai_client import estimate_cost

        if config.PROVIDER == "groq":
            prov_text = f"[bold]Proveedor:[/] Groq — {config.GROQ_MODEL}"
        else:
            prov_text = f"[bold]Proveedor:[/] Anthropic — {config.MODEL}"
        self.query_one("#stat-provider", Static).update(prov_text)

        _, pdfs = estimate_cost(500)
        if config.PROVIDER == "groq":
            quota_text = f"[bold]Cuota Groq:[/] ~{pdfs} PDFs disponibles hoy"
        else:
            quota_text = "[bold]Cuota:[/] Sin límite diario (Anthropic — pago)"
        self.query_one("#stat-quota", Static).update(quota_text)

        pending = count_pending_files()
        self.query_one("#stat-pending", Static).update(
            f"[bold]Pendientes de resumir:[/] {pending}"
        )
        self.query_one("#stat-paths", Static).update(
            f"[bold]Raw:[/] {config.RAW_ROOT}\n"
            f"[bold]Processed:[/] {config.PROCESSED_ROOT}"
        )

        log_widget = self.query_one("#stat-log", RichLog)
        log_widget.clear()
        if config.LOG_FILE.exists():
            lines = config.LOG_FILE.read_text(encoding="utf-8").splitlines()[-20:]
            for line in lines:
                log_widget.write(line)
        else:
            log_widget.write("[dim]Sin logs todavía[/]")


class CarpetasPanel(ScrollableContainer):
    """Folder paths: raw download dir and processed dir."""

    def compose(self) -> ComposeResult:
        import config
        yield Label("Carpetas de trabajo", classes="section-title")
        yield Label(
            "Las carpetas se crean automáticamente al primer uso.",
            classes="help-text",
        )

        yield Label("Descarga (RAW_ROOT):", classes="subsection-label")
        yield Input(str(config.RAW_ROOT), id="input-raw-root",
                    placeholder="./data/raw")
        yield Label(
            "Aquí se guardan los archivos descargados del campus sin modificar.",
            classes="help-text",
        )

        yield Label("Procesado (PROCESSED_ROOT):", classes="subsection-label")
        yield Input(str(config.PROCESSED_ROOT), id="input-processed-root",
                    placeholder="./data/processed")
        yield Label(
            "Aquí se mueven los archivos normalizados listos para resumir.",
            classes="help-text",
        )

        with Horizontal(classes="save-bar"):
            yield Button("Guardar", variant="primary", id="btn-save-carpetas")


class ProveedorPanel(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Proveedor de IA", classes="section-title")
        yield Label(
            "Groq es gratuito con límite diario. Anthropic es pago sin límites.",
            classes="help-text",
        )
        initial = 1 if _config_module.PROVIDER == "anthropic" else 0
        with RadioSet(id="provider-radio"):
            yield RadioButton("Groq  — gratis, llama-3.3-70b (recomendado)", value=(initial == 0))
            yield RadioButton("Anthropic — pago, Claude (sin límites)", value=(initial == 1))

        with Horizontal(classes="save-bar"):
            yield Button("Guardar", variant="primary", id="btn-save-provider")


class ModeloPanel(ScrollableContainer):
    def compose(self) -> ComposeResult:
        import config
        yield Label("Modelo de IA", classes="section-title")

        is_groq = config.PROVIDER == "groq"
        yield Label("Seleccioná el modelo:", classes="subsection-label")
        if is_groq:
            options = [(m, m) for m in GROQ_MODELS]
            current_val = config.GROQ_MODEL
        else:
            options = [(m, m) for m in ANTHROPIC_MODELS]
            current_val = config.MODEL

        yield Select(options, value=current_val, id="model-select")
        yield Static("", id="model-info-box")

        with Collapsible(title="Parámetros avanzados", collapsed=True):
            yield Label("Groq", classes="subsection-label")
            with Horizontal(classes="field-row"):
                yield Label("Chunk size (palabras)", classes="field-label")
                yield Input(str(config.GROQ_CHUNK_SIZE), id="groq-chunk-size",
                            validators=[Number(minimum=100, maximum=10000)])
            with Horizontal(classes="field-row"):
                yield Label("Límite diario (tokens)", classes="field-label")
                yield Input(str(config.GROQ_DAILY_LIMIT), id="groq-daily-limit",
                            validators=[Number(minimum=1000)])

            yield Label("Anthropic", classes="subsection-label")
            with Horizontal(classes="field-row"):
                yield Label("Max tokens respuesta", classes="field-label")
                yield Input(str(config.MAX_TOKENS_RESPONSE), id="max-tokens",
                            validators=[Number(minimum=256, maximum=32000)])
            with Horizontal(classes="field-row"):
                yield Label("Chunk size (palabras)", classes="field-label")
                yield Input(str(config.CHUNK_SIZE), id="anthropic-chunk-size",
                            validators=[Number(minimum=100, maximum=20000)])

        with Horizontal(classes="save-bar"):
            yield Button("Guardar", variant="primary", id="btn-save-modelo")

    def on_mount(self) -> None:
        self._update_model_info()

    def refresh_models(self) -> None:
        """Rebuild model list when PROVIDER changes from another panel."""
        import config
        try:
            sel = self.query_one("#model-select", Select)
        except Exception:
            return

        if config.PROVIDER == "groq":
            options = [(m, m) for m in GROQ_MODELS]
            current_val = config.GROQ_MODEL
        else:
            options = [(m, m) for m in ANTHROPIC_MODELS]
            current_val = config.MODEL

        sel.set_options(options)
        if current_val in [m for m, _ in options]:
            sel.value = current_val
        self._update_model_info()

    def _update_model_info(self) -> None:
        try:
            sel = self.query_one("#model-select", Select)
            model = sel.value
            if model is Select.BLANK:
                return
            model_key = str(model)
            if model_key not in MODEL_INFO:
                return
            info = MODEL_INFO[model_key]
            lines = [
                f"[bold]{info['provider']} — {model}[/]",
                f"  Tipo:    {info['tipo']}",
                f"  Tok/min: {info['tok_min']}",
                f"  Tok/día: {info['tok_dia']}",
                f"  Costo:   {info['costo']}",
                f"  Nota:    {info['nota']}",
            ]
            self.query_one("#model-info-box", Static).update("\n".join(lines))
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "model-select":
            self._update_model_info()


class KeysPanel(ScrollableContainer):
    """API keys and campus credentials."""

    def compose(self) -> ComposeResult:
        import config
        yield Label("Keys y Credenciales", classes="section-title")
        yield Label(
            "Todos los valores se guardan en .env — nunca en el código.",
            classes="help-text",
        )

        yield Label("Groq", classes="subsection-label")
        with Horizontal(classes="field-row"):
            yield Label("GROQ_API_KEY", classes="field-label")
            yield Input(config.GROQ_API_KEY, id="key-groq", password=True,
                        placeholder="gsk_xxxxxxxxxxxxxxxxxxxx")

        yield Label("Anthropic", classes="subsection-label")
        with Horizontal(classes="field-row"):
            yield Label("ANTHROPIC_API_KEY", classes="field-label")
            yield Input(config.ANTHROPIC_API_KEY, id="key-anthropic", password=True,
                        placeholder="sk-ant-xxxxxxxxxxxxxxxxxxxx")

        yield Label("Campus UNO", classes="subsection-label")
        with Horizontal(classes="field-row"):
            yield Label("CAMPUS_USER", classes="field-label")
            yield Input(config.CAMPUS_USER, id="key-campus-user",
                        placeholder="usuario del campus (DNI)")
        with Horizontal(classes="field-row"):
            yield Label("CAMPUS_PASS", classes="field-label")
            yield Input(config.CAMPUS_PASS, id="key-campus-pass", password=True,
                        placeholder="contraseña del campus")

        with Horizontal(classes="save-bar"):
            yield Button("Guardar todo", variant="primary", id="btn-save-keys")


class DrivePanel(ScrollableContainer):
    """Google Drive OAuth configuration."""

    def compose(self) -> ComposeResult:
        import config
        yield Label("Google Drive", classes="section-title")
        yield Label(
            "Drive guarda los resúmenes como Google Docs en tu cuenta personal.",
            classes="help-text",
        )

        yield Label("Setup (una sola vez):", classes="subsection-label")
        yield Label(
            "1. GCP Console → APIs → Habilitar 'Google Drive API'\n"
            "2. Credenciales → Crear → OAuth client ID → Desktop app → Descargar JSON\n"
            "3. Renombrar a credentials.json y ponerlo en la raíz del proyecto\n"
            "4. Click 'Probar conexión' → el navegador pedirá permiso una vez",
            classes="help-text",
        )

        yield Label("credentials.json (DRIVE_CREDENTIALS_FILE):", classes="subsection-label")
        yield Input(str(config.DRIVE_CREDENTIALS_FILE), id="drive-credentials-file",
                    placeholder="credentials.json")

        yield Label("ID carpeta raíz en Drive (DRIVE_PARENT_FOLDER_ID):", classes="subsection-label")
        yield Input(config.DRIVE_PARENT_FOLDER_ID, id="drive-folder-id",
                    placeholder="(vacío = auto-crear 'Resumenes UNO')")
        yield Label(
            "Si está vacío se crea automáticamente la carpeta 'Resumenes UNO' en tu Drive.",
            classes="help-text",
        )

        with Horizontal(classes="exec-row"):
            yield Button("Guardar", variant="primary", id="btn-save-drive")
            yield Button("Probar conexión", variant="default", id="btn-test-drive")

        yield Static("", id="drive-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-test-drive":
            event.stop()
            self.run_worker(self._test_drive_async(), exclusive=True)

    async def _test_drive_async(self) -> None:
        status = self.query_one("#drive-status", Static)
        status.update("[yellow]Conectando a Drive...[/]")
        try:
            import config
            from src.processor.drive_client import DriveClient
            client = await asyncio.to_thread(
                DriveClient.from_oauth,
                config.DRIVE_CREDENTIALS_FILE,
                config.DRIVE_TOKEN_FILE,
            )
            folder_id = await asyncio.to_thread(client.ensure_root_folder)
            status.update(
                f"[green]Conectado. Carpeta raíz: {folder_id}[/]\n"
                "Podés pegar ese ID en DRIVE_PARENT_FOLDER_ID si querés fijarlo."
            )
            folder_input = self.query_one("#drive-folder-id", Input)
            if not folder_input.value:
                folder_input.value = folder_id
        except FileNotFoundError as e:
            status.update(f"[red]credentials.json no encontrado: {e}[/]")
        except Exception as e:
            status.update(f"[red]Error: {e}[/]")


class PromptPanel(ScrollableContainer):
    def compose(self) -> ComposeResult:
        import config
        yield Label("Prompt de resumen (Técnica Feynman)", classes="section-title")
        yield Label(
            "Usá {text} donde debe insertarse el contenido del documento.",
            classes="help-text",
        )
        yield TextArea(config.SUMMARY_PROMPT_TEMPLATE, id="prompt-textarea",
                       language="markdown")
        with Horizontal(classes="save-bar"):
            yield Button("Guardar", variant="primary", id="btn-save-prompt")
            yield Button("Restablecer por defecto", variant="warning",
                         id="btn-reset-prompt")


class EjecutarPanel(ScrollableContainer):
    """3-step execution: Descargar → Organizar → Procesar."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._log_buffer: list[str] = []

    def _log(self, msg: str) -> None:
        """Write to RichLog AND track plain text for copy/save."""
        log_widget = self.query_one("#run-log", RichLog)
        log_widget.write(msg)
        # Strip Rich markup ([bold green], etc.) for plain-text buffer
        plain = re.sub(r"\[/?[a-zA-Z #=]+\]", "", msg)
        self._log_buffer.append(plain)

    def compose(self) -> ComposeResult:
        yield Label("Ejecutar", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Filtro de materia:", classes="field-label")
            yield Input("", id="subject-filter",
                        placeholder="ej: POO II  (vacío = todas)")
        with Horizontal(classes="field-row"):
            yield Label("Año:", classes="field-label")
            yield Input("", id="year-filter",
                        placeholder="ej: 2026  (vacío = todos)")
        with Horizontal(classes="field-row"):
            yield Label("Dry-run (sin API):", classes="field-label")
            yield Switch(False, id="dry-run-switch")
        with Horizontal(classes="field-row"):
            yield Label("Resetear procesados:", classes="field-label")
            yield Switch(False, id="reset-switch")
        with Horizontal(classes="field-row"):
            yield Label("Browser visible:", classes="field-label")
            yield Switch(False, id="visible-switch")

        yield Label("Acciones:", classes="subsection-label")
        with Horizontal(classes="exec-row"):
            yield Button("[1] Descargar",  variant="primary", id="btn-run-download")
            yield Button("[2] Organizar",  variant="default", id="btn-run-organize")
            yield Button("[3] Procesar",   variant="default", id="btn-run-process")
            yield Button("[Todo]",         variant="success", id="btn-run-all")

        with Horizontal(classes="exec-row"):
            yield Label("Log en tiempo real:", classes="subsection-label")
            yield Button("Copiar log",     variant="default", id="btn-copy-log")
            yield Button("Limpiar",        variant="default", id="btn-clear-log")
        yield RichLog(id="run-log", highlight=True, markup=True, max_lines=500)

    def _get_common_kwargs(self) -> dict:
        year_raw = self.query_one("#year-filter", Input).value.strip()
        year_val: int | None
        try:
            year_val = int(year_raw) if year_raw else None
        except ValueError:
            year_val = None
        return {
            "subject_filter": self.query_one("#subject-filter", Input).value.strip() or None,
            "year":           year_val,
            "dry_run":        self.query_one("#dry-run-switch", Switch).value,
            "reset":          self.query_one("#reset-switch", Switch).value,
            "headless":       not self.query_one("#visible-switch", Switch).value,
        }

    async def _run_async(self, mode: str) -> None:
        import main as main_module

        log_widget = self.query_one("#run-log", RichLog)
        log_widget.clear()
        self._log_buffer.clear()
        self._log(f"[bold green]▶ Iniciando modo: {mode}...[/]")

        app_ref = self.app
        panel_ref = self

        class TUILogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.setFormatter(
                    logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
                )

            def emit(self, record):
                msg = self.format(record)
                app_ref.call_from_thread(panel_ref._log, msg)

        handler = TUILogHandler()
        handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        prev_level = root_logger.level
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

        kwargs = self._get_common_kwargs()

        try:
            if mode == "download":
                await asyncio.to_thread(
                    main_module.run,
                    download_only=True,
                    subject_filter=kwargs["subject_filter"],
                    year=kwargs["year"],
                    dry_run=kwargs["dry_run"],
                    headless=kwargs["headless"],
                )
            elif mode == "organize":
                import config
                from src.organizer import organize

                def _org_event(msg: str) -> None:
                    app_ref.call_from_thread(panel_ref._log, msg)

                await asyncio.to_thread(
                    organize,
                    raw_root=config.RAW_ROOT,
                    processed_root=config.PROCESSED_ROOT,
                    dry_run=kwargs["dry_run"],
                    on_event=_org_event,
                )
            elif mode == "process":
                import config
                from src.processor import process

                def _proc_event(msg: str) -> None:
                    app_ref.call_from_thread(panel_ref._log, msg)

                await asyncio.to_thread(
                    process,
                    processed_root=config.PROCESSED_ROOT,
                    drive_parent_folder_id=config.DRIVE_PARENT_FOLDER_ID or None,
                    subject_filter=kwargs["subject_filter"],
                    dry_run=kwargs["dry_run"],
                    reset=kwargs["reset"],
                    on_event=_proc_event,
                )
            elif mode == "all":
                await asyncio.to_thread(
                    main_module.run,
                    subject_filter=kwargs["subject_filter"],
                    year=kwargs["year"],
                    dry_run=kwargs["dry_run"],
                    reset=kwargs["reset"],
                    headless=kwargs["headless"],
                )

            self._log("[bold green]OK Completado.[/]")
        except Exception as exc:
            self._log(f"[bold red]!! Error: {exc}[/]")
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(prev_level)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        mode_map = {
            "btn-run-download": "download",
            "btn-run-organize": "organize",
            "btn-run-process":  "process",
            "btn-run-all":      "all",
        }
        if btn_id in mode_map:
            event.stop()
            self.run_worker(self._run_async(mode_map[btn_id]), exclusive=True)
            return

        if btn_id == "btn-copy-log":
            event.stop()
            self._copy_log()
            return

        if btn_id == "btn-clear-log":
            event.stop()
            self.query_one("#run-log", RichLog).clear()
            self._log_buffer.clear()
            self.app.notify("Log limpiado.", title="OK")
            return

    def _copy_log(self) -> None:
        """Save log to file and try to push to Windows clipboard via clip.exe."""
        if not self._log_buffer:
            self.app.notify("Log vacío. Corré algo primero.", severity="warning")
            return

        text = "\n".join(self._log_buffer)

        # Always save to file as reliable fallback for debugging.
        debug_dir = Path("./data/debug")
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            log_path = debug_dir / "last-run-log.txt"
            log_path.write_text(text, encoding="utf-8")
            saved_msg = f"Guardado en: {log_path.resolve()}"
        except Exception as e:
            saved_msg = f"No se pudo guardar archivo: {e}"

        # Try clipboard via Windows clip.exe (always available on Win10+).
        try:
            subprocess.run(
                ["clip"],
                input=text,
                text=True,
                encoding="utf-8",
                check=True,
                timeout=5,
                shell=True,
            )
            self.app.notify(f"Log copiado al portapapeles. {saved_msg}", title="OK")
        except Exception as e:
            self.app.notify(
                f"Clipboard falló: {e}. {saved_msg}",
                severity="warning",
                title="Atención",
            )


# ── Modal de ayuda ────────────────────────────────────────────

class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cerrar")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("Ayuda — Resumidor Académico UNO", classes="section-title")

            yield Label("Atajos", classes="subsection-label")
            with Horizontal():
                yield Label("[S]", classes="help-key")
                yield Label("Guardar configuración del panel activo")
            with Horizontal():
                yield Label("[Q]", classes="help-key")
                yield Label("Salir")
            with Horizontal():
                yield Label("[↑ / ↓]", classes="help-key")
                yield Label("Navegar entre secciones")
            with Horizontal():
                yield Label("[Escape]", classes="help-key")
                yield Label("Cerrar ayuda")

            yield Label("Paneles", classes="subsection-label")
            for label, desc in [
                ("Estado",    "Stats del sistema y últimas líneas de log"),
                ("Carpetas",  "Rutas raw y processed"),
                ("Proveedor", "Groq (gratis) o Anthropic (pago)"),
                ("Modelo",    "Selector de modelo + límites"),
                ("Keys",      "API keys y credenciales del campus"),
                ("Drive",     "Configurar Google Drive + probar conexión"),
                ("Prompt",    "Template de resumen (Feynman)"),
                ("Ejecutar",  "Descargar / Organizar / Procesar + log"),
            ]:
                with Horizontal():
                    yield Label(label, classes="help-key")
                    yield Label(desc)

            yield Label("Los cambios se guardan en .env", classes="help-text")
            yield Button("Cerrar", variant="primary", id="btn-close-help")

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.dismiss()


# ── App principal ─────────────────────────────────────────────

SIDEBAR_ITEMS = [
    ("Estado",    "pane-estado"),
    ("Carpetas",  "pane-carpetas"),
    ("Proveedor", "pane-proveedor"),
    ("Modelo",    "pane-modelo"),
    ("Keys",      "pane-keys"),
    ("Drive",     "pane-drive"),
    ("Prompt",    "pane-prompt"),
    ("Ejecutar",  "pane-ejecutar"),
]

SAVE_BTN_MAP = {
    "pane-carpetas":  "btn-save-carpetas",
    "pane-proveedor": "btn-save-provider",
    "pane-modelo":    "btn-save-modelo",
    "pane-keys":      "btn-save-keys",
    "pane-drive":     "btn-save-drive",
    "pane-prompt":    "btn-save-prompt",
}


class SummarizerApp(App):
    CSS = APP_CSS
    TITLE = "Resumidor Academico — UNO Campus Edition"
    SUB_TITLE = "Asimov"

    BINDINGS = [
        Binding("s",             "save",     "Guardar",  show=True),
        Binding("q",             "quit",     "Salir",    show=True),
        Binding("question_mark", "help",     "Ayuda",    show=True),
        Binding("up",            "nav_up",   "Arriba",   show=False),
        Binding("down",          "nav_down", "Abajo",    show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with ListView(id="sidebar"):
                for label, pane_id in SIDEBAR_ITEMS:
                    yield ListItem(Label(label), id=f"nav-{pane_id}")
            with ContentSwitcher(initial="pane-estado", id="content-area"):
                yield EstadoPanel(id="pane-estado")
                yield CarpetasPanel(id="pane-carpetas")
                yield ProveedorPanel(id="pane-proveedor")
                yield ModeloPanel(id="pane-modelo")
                yield KeysPanel(id="pane-keys")
                yield DrivePanel(id="pane-drive")
                yield PromptPanel(id="pane-prompt")
                yield EjecutarPanel(id="pane-ejecutar")
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        nav_id = event.item.id or ""
        pane_id = nav_id.removeprefix("nav-")
        if pane_id:
            self.query_one("#content-area", ContentSwitcher).current = pane_id

    def action_nav_up(self) -> None:
        self.query_one("#sidebar", ListView).action_cursor_up()

    def action_nav_down(self) -> None:
        self.query_one("#sidebar", ListView).action_cursor_down()

    def action_save(self) -> None:
        current = self.query_one("#content-area", ContentSwitcher).current
        btn_id = SAVE_BTN_MAP.get(current or "")
        if btn_id:
            try:
                self.query_one(f"#{btn_id}", Button).press()
            except Exception:
                pass

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def _refresh_dependent_panels(self) -> None:
        """Re-render panels whose contents depend on reloaded config."""
        try:
            self.query_one(EstadoPanel).refresh_stats()
        except Exception:
            pass
        try:
            self.query_one(ModeloPanel).refresh_models()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id == "btn-refresh-estado":
            try:
                self.query_one(EstadoPanel).refresh_stats()
                self.notify("Stats actualizados.", title="OK")
            except Exception:
                pass
            return

        if btn_id == "btn-save-carpetas":
            raw_val = self.query_one("#input-raw-root", Input).value.strip()
            proc_val = self.query_one("#input-processed-root", Input).value.strip()
            if raw_val:
                save_to_env("RAW_ROOT", raw_val)
            if proc_val:
                save_to_env("PROCESSED_ROOT", proc_val)
            reload_config()
            self._refresh_dependent_panels()
            self.notify("Carpetas guardadas.", title="Guardado")
            return

        if btn_id == "btn-save-provider":
            rs = self.query_one("#provider-radio", RadioSet)
            value = "anthropic" if rs.pressed_index == 1 else "groq"
            save_to_env("PROVIDER", value)
            reload_config()
            self._refresh_dependent_panels()
            self.notify(f"Proveedor guardado: {value}", title="Guardado")
            return

        if btn_id == "btn-save-modelo":
            sel = self.query_one("#model-select", Select)
            if sel.value is not Select.BLANK:
                model_val = str(sel.value)
                if model_val in GROQ_MODELS:
                    save_to_env("GROQ_MODEL", model_val)
                else:
                    save_to_env("MODEL", model_val)

            for field_id, env_key in [
                ("groq-chunk-size",      "GROQ_CHUNK_SIZE"),
                ("groq-daily-limit",     "GROQ_DAILY_LIMIT"),
                ("max-tokens",           "MAX_TOKENS_RESPONSE"),
                ("anthropic-chunk-size", "CHUNK_SIZE"),
            ]:
                try:
                    val = self.query_one(f"#{field_id}", Input).value.strip()
                    if val:
                        save_to_env(env_key, val)
                except Exception:
                    pass

            reload_config()
            self._refresh_dependent_panels()
            self.notify("Modelo y parámetros guardados.", title="Guardado")
            return

        if btn_id == "btn-save-keys":
            pairs = [
                ("key-groq",          "GROQ_API_KEY"),
                ("key-anthropic",     "ANTHROPIC_API_KEY"),
                ("key-campus-user",   "CAMPUS_USER"),
                ("key-campus-pass",   "CAMPUS_PASS"),
            ]
            for field_id, env_key in pairs:
                try:
                    val = self.query_one(f"#{field_id}", Input).value
                    save_to_env(env_key, val)
                except Exception:
                    pass
            reload_config()
            self.notify("Credenciales guardadas en .env", title="Guardado")
            return

        if btn_id == "btn-save-drive":
            creds_val = self.query_one("#drive-credentials-file", Input).value.strip()
            folder_val = self.query_one("#drive-folder-id", Input).value.strip()
            if creds_val:
                save_to_env("DRIVE_CREDENTIALS_FILE", creds_val)
            if folder_val:
                save_to_env("DRIVE_PARENT_FOLDER_ID", folder_val)
            reload_config()
            self.notify("Configuración de Drive guardada.", title="Guardado")
            return

        if btn_id == "btn-save-prompt":
            text = self.query_one("#prompt-textarea", TextArea).text
            save_to_env("SUMMARY_PROMPT_TEMPLATE", text)
            reload_config()
            self.notify("Prompt guardado.", title="Guardado")
            return

        if btn_id == "btn-reset-prompt":
            self.query_one("#prompt-textarea", TextArea).load_text(_DEFAULT_PROMPT)
            self.notify(
                "Prompt restablecido. Presioná [S] o 'Guardar' para persistirlo.",
                severity="warning", title="Restablecido",
            )
            return


# ── Punto de entrada ─────────────────────────────────────────

if __name__ == "__main__":
    app = SummarizerApp()
    app.run()
