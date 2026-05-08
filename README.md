# Academic Summarizer — UNO Campus Edition

Sistema automático que descarga PDFs del campus UNO, los resume con IA y sube los resúmenes a Google Drive como Google Docs.

---

## Instalación rápida

### 1. Instalar dependencias

```cmd
install.bat
```

O manualmente:
```cmd
pip install anthropic groq pdfplumber python-docx playwright python-dotenv textual google-api-python-client google-auth-httplib2 google-auth-oauthlib
playwright install chromium
```

### 2. Crear el archivo .env

```cmd
copy .env.example .env
```

Completá los valores principales:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
CAMPUS_USER=tu_usuario
CAMPUS_PASS=tu_contraseña
DRIVE_CREDENTIALS_FILE=credentials.json
```

El archivo `.env` **nunca se sube a GitHub** — ya está en `.gitignore`.

### 3. Configurar Google Drive

1. [GCP Console](https://console.cloud.google.com) → Crear proyecto → Habilitar **Google Drive API**
2. Credenciales → Crear → OAuth client ID → tipo **Desktop app** → Descargar JSON
3. Renombrar el archivo descargado a `credentials.json` y ponerlo en la raíz del proyecto
4. Primer run abre el navegador automáticamente para que apruebes → cachea `token.json`

### 4. Lanzar

```cmd
python tui.py
```

---

## TUI (Recomendado)

```cmd
python tui.py
```

8 paneles: **Estado | Carpetas | Proveedor | Modelo | Keys | Drive | Prompt | Ejecutar**

### Panel Ejecutar

| Botón | Acción |
|-------|--------|
| `[1] Descargar` | Scrape Moodle → `data/raw/{materia}/` |
| `[2] Organizar` | Dedup + rename → `data/processed/{materia}/` |
| `[3] Procesar`  | Resumir con IA + subir a Drive |
| `[Todo]`        | Los 3 pasos secuenciales |

El campo **Filtro de materia** acepta año: `POO II 2026` descarga solo el curso de ese año.

### Teclas

| Tecla | Acción |
|-------|--------|
| `S` | Guardar panel activo |
| `Q` | Salir |
| `↑ / ↓` | Navegar secciones |

---

## CLI

```cmd
python main.py                                # pipeline completo
python main.py --dry-run                      # preview sin API calls
python main.py --skip-download                # solo resumir
python main.py --download-only                # solo descargar
python main.py --subject "POO II"             # filtrar por materia
python main.py --subject "POO II 2026"        # filtrar por materia + año
python main.py --reset                        # reprocesar todo
```

### Downloader directo

```cmd
python -m src.downloader --subject "POO II 2026" --raw-root ./data/raw --headless
```

Parámetros:

| Flag | Default | Descripción |
|------|---------|-------------|
| `--subject` | todas | Nombre de materia. Acepta año al final: `"POO II 2026"` o `"POO II 1C2026"` |
| `--year` | actual | Año explícito (override del año en `--subject`) |
| `--raw-root` | `./data/raw` | Carpeta destino |
| `--headless` / `--no-headless` | headless | Mostrar browser |

Los cursos en UNO tienen formato `01017-Álgebra y Geometría Analítica (1C2024)`. El script reconoce este formato automáticamente. Si cursaste la misma materia varios años, especificá el año para descargar la instancia correcta.

---

## Proveedor de IA

Por defecto usa **Groq** (`llama-3.3-70b-versatile`) — completamente gratuito.

| Proveedor | Costo | Límite |
|-----------|-------|--------|
| Groq | Gratis | 100k tokens/día |
| Anthropic | ~$0.10-1.50/mes | Sin límite diario |

Cambiar en `.env`:
```env
PROVIDER=groq          # o anthropic
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Estructura del proyecto

```
main.py                  — CLI entry point + dispatcher (3 pasos)
tui.py                   — TUI Textual (8 paneles)
config.py                — configuración central (lee .env)
.env                     — secretos (no subir)
.env.example             — plantilla
install.bat              — instala dependencias
setup_scheduler.bat      — configura tarea Windows automática
src/
  downloader/            — Playwright Moodle scraper
  organizer/             — dedup + rename + move
  processor/             — extract → summarize → Drive upload
  extractor.py           — pdfplumber + python-docx
  ai_client.py           — Groq + Anthropic
  tracker.py             — hash MD5, registro processed_files.json
data/
  raw/                   — {materia}/{original}.pdf  (no en git)
  processed/             — {materia}/{normalizado}.pdf  (no en git)
```

---

## Solución de problemas

**Login fallido en campus**
→ Verificar `CAMPUS_USER` / `CAMPUS_PASS` en `.env`. Guardar en Keys del TUI y reintentar en la misma sesión.

**`credentials.json` no encontrado**
→ Descargar de GCP Console (ver paso 3 de Configurar Google Drive).

**PDF sin texto extraído**
→ PDF escaneado (imagen). Requiere OCR — no incluido.

**Rate limit Groq**
→ El sistema reintenta automáticamente. Ver cuota en [console.groq.com](https://console.groq.com) → Settings → Limits.

**Logs detallados:**
```
logs/summarizer.log
```

---

## Automatización (opcional)

Ejecutar `setup_scheduler.bat` como administrador para programar el pipeline cada domingo a las 8:00 AM.
