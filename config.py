# ============================================================
#  config.py — Configuración central del sistema
# ============================================================

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

_HERE = Path(__file__).parent

# ----------------------------------------------------------
# ANTHROPIC API
# ----------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS_RESPONSE = int(os.environ.get("MAX_TOKENS_RESPONSE", "4000"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "3000"))

# ----------------------------------------------------------
# PROVEEDOR DE IA
# ----------------------------------------------------------
PROVIDER = os.environ.get("PROVIDER", "groq")

# ----------------------------------------------------------
# GROQ API
# ----------------------------------------------------------
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL      = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_CHUNK_SIZE = int(os.environ.get("GROQ_CHUNK_SIZE", "2000"))
GROQ_DAILY_LIMIT = int(os.environ.get("GROQ_DAILY_LIMIT", "100000"))

# ----------------------------------------------------------
# CAMPUS UNO
# ----------------------------------------------------------
CAMPUS_USER    = os.environ.get("CAMPUS_USER", "")
CAMPUS_PASS    = os.environ.get("CAMPUS_PASS", "")
CAMPUS_HEADLESS = os.environ.get("CAMPUS_HEADLESS", "true").lower() == "true"

# ----------------------------------------------------------
# GOOGLE DRIVE
# ----------------------------------------------------------
DRIVE_CREDENTIALS_FILE = Path(os.environ.get("DRIVE_CREDENTIALS_FILE", str(_HERE / "credentials.json")))
DRIVE_TOKEN_FILE       = Path(os.environ.get("DRIVE_TOKEN_FILE",       str(_HERE / "token.json")))
DRIVE_PARENT_FOLDER_ID = os.environ.get("DRIVE_PARENT_FOLDER_ID", "")

# ----------------------------------------------------------
# RUTAS
# ----------------------------------------------------------
RAW_ROOT       = Path(os.environ.get("RAW_ROOT",       str(_HERE / "data" / "raw")))
PROCESSED_ROOT = Path(os.environ.get("PROCESSED_ROOT", str(_HERE / "data" / "processed")))


PROCESSED_LOG = _HERE / "processed_files.json"
LOG_FILE      = _HERE / "logs" / "summarizer.log"

# ----------------------------------------------------------
# EXTENSIONES SOPORTADAS
# ----------------------------------------------------------
SUPPORTED_EXTENSIONS = [".pdf", ".docx"]

# ----------------------------------------------------------
# PROMPT DE RESUMEN
# ----------------------------------------------------------
SUMMARY_PROMPT_TEMPLATE = os.environ.get("SUMMARY_PROMPT_TEMPLATE", """Eres un asistente académico experto y utilizas la tecnica de feynman de forma perfecta para hacer los resumens. Analiza el siguiente contenido universitario y genera un resumen estructurado.

CONTENIDO:
{text}

Genera un resumen con esta estructura exacta en Markdown:

## Tema Central
[Una oración que capture la idea principal]

##Conceptos Clave
- [Concepto 1]: [Definición breve]
- [Concepto 2]: [Definición breve]
- [Concepto 3]: [Definición breve]
(máximo 8 conceptos)

## Desarrollo
[3 párrafo explicando el contenido de forma clara y ordenada]

##Conexiones
[Menciona brevemente cómo este tema se relaciona con otros conceptos o áreas]

##Preguntas para el Examen
1. [Pregunta probable 1]
2. [Pregunta probable 2]
3. [Pregunta probable 3]

Sé conciso pero completo. Usa lenguaje académico claro. Recomienda tambien tecnicas de estudio como un pequeño bonus para el estudiante.

Si el archivo analizado es un parcial quiero que le recomiendes que contenidos son necesarios para completar este parcial   . """)
