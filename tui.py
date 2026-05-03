# ============================================================
#  tui.py — Interfaz TUI para Academic Summarizer (UNO)
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
import sys
from pathlib import Path

# Asegurar que el proyecto raíz esté en el path
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
    "claude-sonnet-4-5",
    "claude-opus-4-5",
]

# Límites y costos de cada modelo (para mostrar al usuario)
MODEL_INFO: dict[str, dict] = {
    # Groq
    "llama-3.3-70b-versatile": {
        "provider": "Groq",
        "tipo": "Gratis",
        "req_min": 30,
        "tok_min": "6,000",
        "tok_dia": "100,000",
        "costo": "—",
        "nota": "Más potente de Groq",
    },
    "llama-3.1-8b-instant": {
        "provider": "Groq",
        "tipo": "Gratis",
        "req_min": 30,
        "tok_min": "20,000",
        "tok_dia": "500,000",
        "costo": "—",
        "nota": "Más rápido, menor calidad",
    },
    "gemma2-9b-it": {
        "provider": "Groq",
        "tipo": "Gratis",
        "req_min": 30,
        "tok_min": "15,000",
        "tok_dia": "250,000",
        "costo": "—",
        "nota": "Buen balance velocidad/calidad",
    },
    "mixtral-8x7b-32768": {
        "provider": "Groq",
        "tipo": "Gratis",
        "req_min": 30,
        "tok_min": "5,000",
        "tok_dia": "100,000",
        "costo": "—",
        "nota": "Ventana de contexto grande (32k)",
    },
    # Anthropic
    "claude-haiku-4-5-20251001": {
        "provider": "Anthropic",
        "tipo": "Pago",
        "req_min": "—",
        "tok_min": "—",
        "tok_dia": "Sin límite",
        "costo": "$0.25/M tok entrada",
        "nota": "Rápido y económico",
    },
    "claude-sonnet-4-5": {
        "provider": "Anthropic",
        "tipo": "Pago",
        "req_min": "—",
        "tok_min": "—",
        "tok_dia": "Sin límite",
        "costo": "$3.00/M tok entrada",
        "nota": "Balance calidad/costo",
    },
    "claude-opus-4-5": {
        "provider": "Anthropic",
        "tipo": "Pago",
        "req_min": "—",
        "tok_min": "—",
        "tok_dia": "Sin límite",
        "costo": "$15.00/M tok entrada",
        "nota": "El más potente",
    },
}

# Prompt por defecto (capturado al inicio para el botón "Restablecer")
_DEFAULT_PROMPT = _config_module.SUMMARY_PROMPT_TEMPLATE

DOTENV_PATH = Path(__file__).parent / ".env"


# ── Helpers de configuración ─────────────────────────────────

def save_to_env(key: str, value: str) -> None:
    """Guarda key=value en el archivo .env."""
    try:
        from dotenv import set_key
        set_key(str(DOTENV_PATH), key, value, quote_mode="never")
    except ImportError:
        pass  # Si no hay dotenv, no podemos guardar


def reload_config() -> None:
    """Recarga config.py y src/ai_client.py tras guardar el .env."""
    try:
        from dotenv import load_dotenv
        load_dotenv(DOTENV_PATH, override=True)
    except ImportError:
        pass
    importlib.reload(_config_module)
    try:
        import src.ai_client as _ai
        importlib.reload(_ai)
    except Exception:
        pass


def count_pending_files() -> int:
    """Cuenta archivos pendientes de procesar en DOCUMENTS_ROOT."""
    try:
        from src.tracker import load_processed, is_processed
        processed = load_processed(_config_module.PROCESSED_LOG)
        root = _config_module.DOCUMENTS_ROOT
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
    width: 20;
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

/* Cada panel es scrollable */
EstadoPanel, ProveedorPanel, ModeloPanel,
KeysPanel, PromptPanel, EjecutarPanel {
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
    width: 26;
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

/* Estado panel */
.stat-box {
    border: solid $primary-darken-2;
    padding: 1 2;
    margin-bottom: 1;
    height: auto;
    background: $surface-darken-1;
}

/* Log panel */
#stat-log, #run-log {
    height: 12;
    border: solid $primary-darken-2;
    margin-top: 1;
    background: $surface-darken-2;
}

/* TextArea prompt */
#prompt-textarea {
    height: 22;
    border: solid $primary-darken-2;
    margin-top: 1;
}

/* Model info box */
#model-info-box {
    border: solid $accent-darken-2;
    padding: 1 2;
    margin-top: 1;
    height: auto;
    background: $surface-darken-1;
}

/* Ejecutar buttons */
.exec-row {
    height: auto;
    margin-top: 1;
}

.exec-row Button {
    margin-right: 1;
}

/* Modal de ayuda */
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
    width: 16;
    text-style: bold;
    color: $accent;
}
"""


# ── Paneles ───────────────────────────────────────────────────

class EstadoPanel(ScrollableContainer):
    """Panel de estado — muestra stats y permite editar DOCUMENTS_ROOT."""

    def compose(self) -> ComposeResult:
        import config
        yield Label("Estado del sistema", classes="section-title")

        with Vertical(classes="stat-box"):
            yield Static("", id="stat-provider")
            yield Static("", id="stat-quota")
            yield Static("", id="stat-pending")

        yield Label("Carpeta de documentos (DOCUMENTS_ROOT):", classes="subsection-label")
        yield Input(str(config.DOCUMENTS_ROOT), id="documents-root",
                    placeholder=r"C:\Users\...\Documentos")
        yield Label(
            "Es la carpeta donde tenés tus PDFs/Word organizados por materia.",
            classes="help-text",
        )

        yield Label("Últimas líneas del log:", classes="subsection-label")
        yield RichLog(id="stat-log", highlight=True, markup=True, max_lines=30)

        with Horizontal(classes="save-bar"):
            yield Button("Guardar carpeta", variant="primary", id="btn-save-estado")
            yield Button("Actualizar stats", variant="default", id="btn-refresh-estado")

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
            f"[bold]Archivos pendientes:[/] {pending}"
        )

        log_widget = self.query_one("#stat-log", RichLog)
        log_widget.clear()
        if config.LOG_FILE.exists():
            lines = config.LOG_FILE.read_text(encoding="utf-8").splitlines()[-20:]
            for line in lines:
                log_widget.write(line)
        else:
            log_widget.write("[dim]Sin logs todavía[/]")


class ProveedorPanel(ScrollableContainer):
    """Panel para elegir entre Groq y Anthropic."""

    def compose(self) -> ComposeResult:
        import config
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
    """Panel para elegir modelo con info de límites y parámetros avanzados."""

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
                yield Input(
                    str(config.GROQ_CHUNK_SIZE),
                    id="groq-chunk-size",
                    validators=[Number(minimum=100, maximum=10000)],
                )
            with Horizontal(classes="field-row"):
                yield Label("Límite diario (tokens)", classes="field-label")
                yield Input(
                    str(config.GROQ_DAILY_LIMIT),
                    id="groq-daily-limit",
                    validators=[Number(minimum=1000)],
                )

            yield Label("Anthropic", classes="subsection-label")
            with Horizontal(classes="field-row"):
                yield Label("Max tokens respuesta", classes="field-label")
                yield Input(
                    str(config.MAX_TOKENS_RESPONSE),
                    id="max-tokens",
                    validators=[Number(minimum=256, maximum=32000)],
                )
            with Horizontal(classes="field-row"):
                yield Label("Chunk size (palabras)", classes="field-label")
                yield Input(
                    str(config.CHUNK_SIZE),
                    id="anthropic-chunk-size",
                    validators=[Number(minimum=100, maximum=20000)],
                )

        with Horizontal(classes="save-bar"):
            yield Button("Guardar", variant="primary", id="btn-save-modelo")

    def on_mount(self) -> None:
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
                f"  Tipo:      {info['tipo']}",
                f"  Req/min:   {info['req_min']}",
                f"  Tok/min:   {info['tok_min']}",
                f"  Tok/día:   {info['tok_dia']}",
                f"  Costo:     {info['costo']}",
                f"  Nota:      {info['nota']}",
            ]
            self.query_one("#model-info-box", Static).update("\n".join(lines))
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "model-select":
            self._update_model_info()


class KeysPanel(ScrollableContainer):
    """Panel unificado: API keys + credenciales del campus + Notion."""

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
            yield Input(
                config.CAMPUS_USER,
                id="key-campus-user",
                placeholder="usuario del campus",
            )
        with Horizontal(classes="field-row"):
            yield Label("CAMPUS_PASS", classes="field-label")
            yield Input(
                config.CAMPUS_PASS,
                id="key-campus-pass",
                password=True,
                placeholder="contraseña del campus",
            )

        yield Label("Notion", classes="subsection-label")
        with Horizontal(classes="field-row"):
            yield Label("NOTION_TOKEN", classes="field-label")
            yield Input(config.NOTION_TOKEN, id="key-notion-token", password=True,
                        placeholder="secret_xxxxxxxxxxxxxxxxxxxx")
        with Horizontal(classes="field-row"):
            yield Label("NOTION_DATABASE_ID", classes="field-label")
            yield Input(config.NOTION_DATABASE_ID, id="key-notion-db",
                        placeholder="32 caracteres del ID de la base de datos")
        yield Label(
            "El Database ID son los 32 chars en la URL de Notion entre la última '/' y el '?'.",
            classes="help-text",
        )

        with Horizontal(classes="save-bar"):
            yield Button("Guardar todo", variant="primary", id="btn-save-keys")


class PromptPanel(ScrollableContainer):
    """Panel para editar el prompt de resumen."""

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
    """Panel para lanzar el procesamiento con log en tiempo real."""

    def compose(self) -> ComposeResult:
        yield Label("Ejecutar procesamiento", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Filtro de materia:", classes="field-label")
            yield Input("", id="subject-filter",
                        placeholder="ej: Matematicas (dejar vacío para todas)")
        with Horizontal(classes="field-row"):
            yield Label("Resetear procesados:", classes="field-label")
            yield Switch(False, id="reset-switch")

        with Horizontal(classes="exec-row"):
            yield Button("Ejecutar completo", variant="success", id="btn-run-full")
            yield Button("Solo descargar",   variant="default", id="btn-run-download")
            yield Button("Solo resumir",     variant="default", id="btn-run-summarize")
            yield Button("Dry-run",          variant="warning", id="btn-run-dry")

        yield Label("Log en tiempo real:", classes="subsection-label")
        yield RichLog(id="run-log", highlight=True, markup=True, max_lines=500)

    def _get_run_kwargs(self, mode: str) -> dict:
        subject = self.query_one("#subject-filter", Input).value.strip() or None
        reset   = self.query_one("#reset-switch", Switch).value
        return {
            "dry_run":       mode == "dry",
            "subject_filter": subject,
            "reset":         reset,
            "skip_download": mode == "summarize",
            "download_only": mode == "download",
        }

    async def _run_main_async(self, mode: str) -> None:
        import main as main_module

        log_widget = self.query_one("#run-log", RichLog)
        log_widget.clear()
        log_widget.write("[bold green]▶ Iniciando...[/]")

        app_ref = self.app

        class TUILogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.setFormatter(
                    logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
                )

            def emit(self, record):
                msg = self.format(record)
                app_ref.call_from_thread(log_widget.write, msg)

        handler = TUILogHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        kwargs = self._get_run_kwargs(mode)
        try:
            await asyncio.to_thread(main_module.run, **kwargs)
            log_widget.write("[bold green]OK Completado.[/]")
        except Exception as exc:
            log_widget.write(f"[bold red]!! Error: {exc}[/]")
        finally:
            root_logger.removeHandler(handler)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mode_map = {
            "btn-run-full":      "full",
            "btn-run-download":  "download",
            "btn-run-summarize": "summarize",
            "btn-run-dry":       "dry",
        }
        button_id = event.button.id
        if button_id is None:
            return
        mode = mode_map.get(button_id)
        if mode:
            event.stop()
            self.run_worker(self._run_main_async(mode), exclusive=True)


# ── Modal de ayuda ────────────────────────────────────────────

class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", "Cerrar")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("Ayuda — Resumidor Académico UNO", classes="section-title")
            with Vertical():

    # 🔹 Atajos
                yield Label("Atajos", classes="subsection-label")

        with Horizontal():
            yield Label("[S]", classes="help-key")
            yield Label("Guardar configuración del panel activo")

        with Horizontal():
            yield Label("[Q]", classes="help-key")
            yield Label("Salir")

        with Horizontal():
            yield Label("[↑ / ↓]", classes="help-key")
            yield Label("Navegar entre secciones del sidebar")

        with Horizontal():
            yield Label("[Escape]", classes="help-key")
            yield Label("Cerrar esta ayuda")

        # 🔹 Secciones
        yield Label("Secciones", classes="subsection-label")

        with Horizontal():
            yield Label("Estado", classes="help-key")
            yield Label("Stats del sistema + carpeta de documentos")

        with Horizontal():
            yield Label("Proveedor", classes="help-key")
            yield Label("Elegir Groq (gratis) o Anthropic (pago)")

        with Horizontal():
            yield Label("Modelo", classes="help-key")
            yield Label("Selector de modelo + límites + parámetros")

        with Horizontal():
            yield Label("Keys", classes="help-key")
            yield Label("API keys, credenciales del campus y Notion")

        with Horizontal():
            yield Label("Prompt", classes="help-key")
            yield Label("Template de resumen (técnica Feynman)")

        with Horizontal():
            yield Label("Ejecutar", classes="help-key")
            yield Label("Procesamiento con log en tiempo real")

        yield Label("Los cambios se guardan en el archivo .env.", classes="help-text")
        yield Button("Cerrar", variant="primary", id="btn-close-help")

        def on_button_pressed(self, _: Button.Pressed) -> None:
            self.dismiss()


# ── App principal ─────────────────────────────────────────────

SIDEBAR_ITEMS = [
    ("Estado",    "pane-estado"),
    ("Proveedor", "pane-proveedor"),
    ("Modelo",    "pane-modelo"),
    ("Keys",      "pane-keys"),
    ("Prompt",    "pane-prompt"),
    ("Ejecutar",  "pane-ejecutar"),
]

SAVE_BTN_MAP = {
    "pane-estado":    "btn-save-estado",
    "pane-proveedor": "btn-save-provider",
    "pane-modelo":    "btn-save-modelo",
    "pane-keys":      "btn-save-keys",
    "pane-prompt":    "btn-save-prompt",
}


class SummarizerApp(App):
    CSS = APP_CSS
    TITLE = "Resumidor Academico — UNO Campus Edition"
    SUB_TITLE = "Academic Summarizer"

    BINDINGS = [
        Binding("s",             "save",     "Guardar",   show=True),
        Binding("q",             "quit",     "Salir",     show=True),
        Binding("question_mark", "help",     "Ayuda",     show=True),
        Binding("up",            "nav_up",   "Arriba",    show=False),
        Binding("down",          "nav_down", "Abajo",     show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with ListView(id="sidebar"):
                for label, pane_id in SIDEBAR_ITEMS:
                    yield ListItem(Label(label), id=f"nav-{pane_id}")
            with ContentSwitcher(initial="pane-estado", id="content-area"):
                yield EstadoPanel(id="pane-estado")
                yield ProveedorPanel(id="pane-proveedor")
                yield ModeloPanel(id="pane-modelo")
                yield KeysPanel(id="pane-keys")
                yield PromptPanel(id="pane-prompt")
                yield EjecutarPanel(id="pane-ejecutar")
        yield Footer()

    # ── Navegación ────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        nav_id = event.item.id or ""
        pane_id = nav_id.removeprefix("nav-")
        if pane_id:
            self.query_one("#content-area", ContentSwitcher).current = pane_id

    def action_nav_up(self) -> None:
        lv = self.query_one("#sidebar", ListView)
        lv.action_cursor_up()

    def action_nav_down(self) -> None:
        lv = self.query_one("#sidebar", ListView)
        lv.action_cursor_down()

    # ── Acciones de teclas ───────────────────────────────────

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

    # ── Guardado por panel ───────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        # ── Estado ──────────────────────────────────────────
        if btn_id == "btn-save-estado":
            val = self.query_one("#documents-root", Input).value.strip()
            if val:
                save_to_env("DOCUMENTS_ROOT", val)
                reload_config()
                self.notify("Carpeta de documentos guardada.", title="Guardado")
            return

        if btn_id == "btn-refresh-estado":
            try:
                self.query_one(EstadoPanel).refresh_stats()
                self.notify("Stats actualizados.", title="OK")
            except Exception:
                pass
            return

        # ── Proveedor ────────────────────────────────────────
        if btn_id == "btn-save-provider":
            rs = self.query_one("#provider-radio", RadioSet)
            value = "anthropic" if rs.pressed_index == 1 else "groq"
            save_to_env("PROVIDER", value)
            reload_config()
            self.notify(f"Proveedor guardado: {value}", title="Guardado")
            return

        # ── Modelo ───────────────────────────────────────────
        if btn_id == "btn-save-modelo":
            sel = self.query_one("#model-select", Select)
            if sel.value is not Select.BLANK:
                model_val = str(sel.value)
                # Guardar en la variable correcta según proveedor
                if model_val in GROQ_MODELS:
                    save_to_env("GROQ_MODEL", model_val)
                else:
                    save_to_env("MODEL", model_val)

            # Parámetros avanzados
            for field_id, env_key in [
                ("groq-chunk-size",     "GROQ_CHUNK_SIZE"),
                ("groq-daily-limit",    "GROQ_DAILY_LIMIT"),
                ("max-tokens",          "MAX_TOKENS_RESPONSE"),
                ("anthropic-chunk-size","CHUNK_SIZE"),
            ]:
                try:
                    val = self.query_one(f"#{field_id}", Input).value.strip()
                    if val:
                        save_to_env(env_key, val)
                except Exception:
                    pass

            reload_config()
            self.notify("Modelo y parámetros guardados.", title="Guardado")
            return

        # ── Keys ─────────────────────────────────────────────
        if btn_id == "btn-save-keys":
            pairs = [
                ("key-groq",          "GROQ_API_KEY"),
                ("key-anthropic",     "ANTHROPIC_API_KEY"),
                ("key-campus-user",   "CAMPUS_USER"),
                ("key-campus-pass",   "CAMPUS_PASS"),
                ("key-notion-token",  "NOTION_TOKEN"),
                ("key-notion-db",     "NOTION_DATABASE_ID"),
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

        # ── Prompt ───────────────────────────────────────────
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
                severity="warning",
                title="Restablecido",
            )
            return


# ── Punto de entrada ─────────────────────────────────────────

if __name__ == "__main__":
    app = SummarizerApp()
    app.run()
