# ============================================================
#  config.py — Configuración central del sistema
#  Editá este archivo para personalizar el comportamiento
# ============================================================

import os
from pathlib import Path

# Carga el archivo .env si existe (no falla si no está)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv no instalado, se usan las env vars del sistema

# ----------------------------------------------------------
# ANTHROPIC API
# ----------------------------------------------------------
# Recomendado: variable de entorno (más seguro)
#   En CMD:  set ANTHROPIC_API_KEY=sk-ant-xxxxx
#   En PS:   $env:ANTHROPIC_API_KEY="sk-ant-xxxxx"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Modelo a usar para Anthropic
MODEL = "claude-haiku-4-5-20251001"

MAX_TOKENS_RESPONSE = 4000   # Tokens máximos en el resumen; si se corta a la mitad, aumentá este valor
CHUNK_SIZE = 3000            # Palabras por chunk para Anthropic

# ----------------------------------------------------------
# PROVEEDOR DE IA
# ----------------------------------------------------------
# "groq"      → gratis, usa llama-3.3-70b-versatile (recomendado para empezar)
# "anthropic" → pago, usa Claude Haiku (más potente, sin límites diarios)
PROVIDER = os.environ.get("PROVIDER", "groq")

# ----------------------------------------------------------
# GROQ API  (solo si PROVIDER = "groq")
# ----------------------------------------------------------
#   En CMD:  set GROQ_API_KEY=gsk_xxxxx
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL       = "llama-3.3-70b-versatile"
GROQ_CHUNK_SIZE  = 2000       # chunks más chicos por el límite de 6000 tok/min
GROQ_DAILY_LIMIT = 100_000    # tokens/día del free tier

# ----------------------------------------------------------
# NOTION API
# ----------------------------------------------------------
# Token de integración de Notion (Internal Integration Token)
#   En CMD:  set NOTION_TOKEN=secret_xxxxx
# ID de la base de datos donde se guardarán los resúmenes
#   En CMD:  set NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

# ----------------------------------------------------------
# CAMPUS UNO
# ----------------------------------------------------------
CAMPUS_USER = os.environ.get("CAMPUS_USER", "")
CAMPUS_PASS = os.environ.get("CAMPUS_PASS", "")

# ----------------------------------------------------------
# RUTAS
# ----------------------------------------------------------
# Carpeta raíz donde están tus documentos organizados por materia
# Se puede setear en .env como: DOCUMENTS_ROOT=C:\Users\TuNombre\Documentos\Universidad
DOCUMENTS_ROOT = Path(os.environ.get(
    "DOCUMENTS_ROOT",
    r"C:\Users\Asus\OneDrive\Escritorio\Materiales facu\problematica regional"
))

# Archivo donde se registran los documentos ya procesados
# (para no procesar dos veces el mismo archivo)
PROCESSED_LOG = Path(__file__).parent / "processed_files.json"

# Archivo de logs del sistema
LOG_FILE = Path(__file__).parent / "logs" / "summarizer.log"

# ----------------------------------------------------------
# EXTENSIONES SOPORTADAS
# ----------------------------------------------------------
SUPPORTED_EXTENSIONS = [".pdf", ".docx"]

# ----------------------------------------------------------
# PROMPT DE RESUMEN
# ----------------------------------------------------------
# Personalizá el formato del resumen según tu preferencia
SUMMARY_PROMPT_TEMPLATE = """Eres un asistente académico experto y utilizas la tecnica de feynman de forma perfecta para hacer los resumens. Analiza el siguiente contenido universitario y genera un resumen estructurado.

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

Si el archivo analizado es un parcial quiero que le recomiendes que contenidos son necesarios para completar este parcial   . """
