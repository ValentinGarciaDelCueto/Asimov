# 📚 Academic Summarizer

Sistema automático que lee tus documentos universitarios (PDF y Word), los resume con IA y guarda los resultados en Notion, organizado por materia.

---

## ⚡ Instalación rápida con Docker (recomendado)

> **No necesitás instalar Python ni ninguna dependencia.** Solo Docker Desktop.

### 1. Instalar Docker Desktop
Descargalo desde https://www.docker.com/products/docker-desktop/ e instalalo como administrador. Abrilo antes de continuar.

### 2. Crear tu carpeta de trabajo
Creá una carpeta vacía en cualquier lugar y dentro de ella:
- Descargá `docker-compose.yml` y `.env.example` desde el repositorio
- Renombrá `.env.example` a `.env`
- Creá una carpeta llamada `documentos`

La estructura debe quedar así:
```
mi-carpeta/
├── docker-compose.yml
├── .env
└── documentos/     ← acá van tus PDFs y DOCX
```

### 3. Completar el archivo .env
Abrí `.env` con el Bloc de notas y completá tus credenciales:
```env
PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
CAMPUS_USER=tu_usuario
CAMPUS_PASS=tu_contraseña
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
El archivo `.env` **nunca se sube a GitHub** — ya está en `.gitignore`.

### 4. Obtener las API keys
- **Groq (gratis):** https://console.groq.com → API Keys
- **Notion:** https://www.notion.so/my-integrations → New Integration → copiar token
- **Anthropic (solo si usás `PROVIDER=anthropic`):** https://console.anthropic.com → API Keys

### 5. Lanzar el bot
Abrí una terminal (CMD) en tu carpeta y corré:
```cmd
docker compose run --rm bot python main.py
```
La primera vez Docker descarga la imagen automáticamente (~5 minutos). Las siguientes veces arranca en segundos.

---

## 🔧 Instalación manual (sin Docker)

Si preferís instalar Python directamente en tu máquina:

### 1. Instalar dependencias
```
install.bat
```
O manualmente:
```cmd
pip install anthropic groq pdfplumber python-docx notion-client playwright python-dotenv textual
playwright install chromium
```

### 2. Crear el archivo .env
```cmd
copy .env.example .env
```
Completá tus valores en `.env` (ver sección anterior).

### 3. Lanzar la interfaz
```cmd
python tui.py
```

---

## 🖥️ Interfaz TUI (Recomendado)

```cmd
python tui.py
```

Abre una interfaz de pantalla completa en la terminal para configurar el sistema sin tocar archivos.

```
┌──────────────────────────────────────────────────────────────┐
│  Resumidor Academico — UNO Campus Edition        [Header]    │
├────────────┬─────────────────────────────────────────────────┤
│ > Estado   │  Estado del sistema                             │
│  Proveedor │  Proveedor: Groq — llama-3.3-70b-versatile      │
│  Modelo    │  Cuota Groq: ~47 PDFs disponibles hoy           │
│  Keys      │  Archivos pendientes: 3                         │
│  Prompt    │                                                 │
│  Ejecutar  │  Carpeta de documentos:                         │
│            │  [C:\Users\...\Materiales facu            ]     │
├────────────┴─────────────────────────────────────────────────┤
│  [S] Guardar  [↑↓] Navegar  [?] Ayuda  [Q] Salir            │
└──────────────────────────────────────────────────────────────┘
```

### Secciones

| Sección | Qué podés hacer |
|---------|-----------------|
| **Estado** | Ver stats del sistema, cuota de Groq, archivos pendientes, log reciente. Cambiar la carpeta de documentos. |
| **Proveedor** | Elegir entre Groq (gratis) y Anthropic (pago) |
| **Modelo** | Seleccionar modelo con tabla de límites (req/min, tokens/día, costo). Expandir parámetros avanzados (chunk size, max tokens). |
| **Keys** | Configurar todas las credenciales: Groq API key, Anthropic API key, usuario/clave del campus, token y database ID de Notion. |
| **Prompt** | Editar el prompt de resumen (técnica Feynman). Botón para restablecer al default. |
| **Ejecutar** | Lanzar el procesamiento con log en tiempo real. Modos: completo, solo descargar, solo resumir, dry-run. Filtro por materia. |

### Teclas

| Tecla | Acción |
|-------|--------|
| `S` | Guardar la configuración del panel activo |
| `Q` | Salir |
| `?` | Mostrar ayuda |
| `↑ / ↓` | Navegar entre secciones |
| `Escape` | Cerrar modal de ayuda |

Los cambios se guardan en `.env` — nunca en el código.

---

## 🗂️ Configuración de Notion

### Crear la base de datos
Creá una base de datos en Notion con estas propiedades:

| Propiedad | Tipo   | Descripción                     |
|-----------|--------|---------------------------------|
| Nombre    | Título | Nombre del archivo PDF/DOCX     |
| Materia   | Texto  | Nombre de la materia            |
| Fecha     | Fecha  | Fecha de generación del resumen |
| Estado    | Select | Pendiente / Leído / Repasado    |

El campo **Estado** te permite filtrar en Notion qué resúmenes ya repasaste antes de un parcial.

### Obtener el token de Notion
1. Ir a https://www.notion.so/my-integrations
2. Crear nueva integración → Internal Integration
3. Abrir la base de datos en Notion → Connections → conectar tu integración

### Obtener el Database ID
El ID está en la URL de tu base de datos:
```
https://www.notion.so/TuNombre/ESTE-ES-EL-ID?v=...
```
Es la parte de 32 caracteres entre la última `/` y el `?`.

---

## 📁 Estructura de carpetas

### Tu carpeta de documentos (input):
```
Universidad/
├── Matemáticas/
│   ├── clase1_integrales.pdf
│   └── guia_practica.docx
├── Historia/
│   └── unidad2_revolucion.pdf
└── Programación/
    └── apuntes_algoritmos.docx
```

### Tu base de datos en Notion (output):
```
📚 Resumenes Facu
├── clase1_integrales.pdf     → Matemáticas  → Pendiente
├── guia_practica.docx        → Matemáticas  → Leído
├── unidad2_revolucion.pdf    → Historia     → Repasado
└── apuntes_algoritmos.docx   → Programación → Pendiente
```

---

## 📥 Descarga de campus

Descarga el archivo más reciente de una materia específica directamente desde el campus virtual de UNO.

### Configurar credenciales del campus
```cmd
set CAMPUS_USER=tu_usuario
set CAMPUS_PASS=tu_contraseña
```
O pasar las credenciales directamente con `--usuario` y `--clave`.

### Uso básico
```cmd
python campus_downloader.py --materia "Problemática Regional" --dest "C:\Descargas"
```

### Especificar año (útil para materias recursadas)
```cmd
python campus_downloader.py --materia "Álgebra" --año 2026 --dest "C:\Descargas"
```

### Con credenciales explícitas
```cmd
python campus_downloader.py --materia "Análisis Matemático" --año 2026 --dest "C:\Descargas" --usuario minombre --clave mipassword
```

### Parámetros disponibles

| Parámetro   | Requerido | Descripción |
|-------------|-----------|-------------|
| `--materia` | Sí | Nombre parcial de la materia (sin acentos también funciona) |
| `--año`     | No | Año del curso. Por defecto usa el año actual |
| `--dest`    | Sí | Carpeta donde guardar el archivo descargado |
| `--usuario` | No | Usuario del campus (alternativa a `CAMPUS_USER`) |
| `--clave`   | No | Contraseña del campus (alternativa a `CAMPUS_PASS`) |

### Notas
- Los cursos en UNO tienen el formato `01017-Álgebra y Geometría Analítica (1C2024)`. El script reconoce este formato automáticamente.
- Si cursaste la misma materia dos veces, especificá `--año` para distinguir entre instancias.
- El script descarga únicamente el archivo más reciente del curso (detecta timestamps de Moodle; si no hay, toma el último de la lista).
- Se descargan solo archivos PDF y DOCX.

---

## 🖥️ Comandos disponibles

### Con Docker (recomendado)

| Comando | Descripción |
|---------|-------------|
| `docker compose run --rm bot python main.py` | Descarga del campus + resume archivos nuevos |
| `docker compose run --rm bot python main.py --dry-run` | Muestra qué procesaría (sin gastar tokens) |
| `docker compose run --rm bot python main.py --reset` | Reprocesa todos los archivos desde cero |
| `docker compose run --rm bot python main.py --skip-download` | Solo resume, sin ir al campus |
| `docker compose run --rm bot python main.py --download-only` | Solo descarga del campus, sin resumir |
| `docker compose run --rm bot python main.py --subject "Matemáticas"` | Solo procesa esa materia |
| `docker compose run --rm bot python tui.py` | Abre la interfaz visual TUI |

### Sin Docker (instalación manual)

| Comando | Descripción |
|---------|-------------|
| `python main.py` | Procesa archivos nuevos |
| `python main.py --dry-run` | Muestra qué procesaría (sin gastar tokens) |
| `python main.py --reset` | Reprocesa todos los archivos desde cero |
| `python main.py --subject "Matemáticas"` | Solo procesa esa materia |
| `python main.py --subject "mat" --dry-run` | Búsqueda parcial + modo prueba |

---

## ⏰ Automatización (domingo 8:00 AM)

1. Abrir `setup_scheduler.bat` con clic derecho → **Ejecutar como administrador**
2. Editar las variables `PROJECT_DIR` y `PYTHON_PATH` dentro del archivo
3. Ejecutarlo

Para ejecutar manualmente desde CMD:
```cmd
schtasks /run /tn "AcademicSummarizer"
```

---

## 🤖 Proveedor de IA: Groq (gratis) vs Anthropic

Por defecto el sistema usa **Groq** con `llama-3.3-70b-versatile`, que es completamente gratuito.

### Configurar Groq (por defecto)
1. Ir a https://console.groq.com → API Keys → Create API Key
2. En CMD:
```cmd
set GROQ_API_KEY=gsk_tu-key-aqui
```
Groq ya es el default — no hace falta setear `PROVIDER`.

### Límites del free tier de Groq

| Límite | Cantidad |
|--------|----------|
| Requests por minuto | 30 |
| Tokens por minuto | 6.000 |
| Tokens por día | 100.000 |

**¿Cuántos PDFs podés procesar?** Un PDF típico de facu usa ~3.000-5.000 tokens, entonces:
- Por día: ~20-30 PDFs antes de llegar al límite
- Por minuto: 1 PDF cada ~30-60 segundos (el sistema lo maneja automáticamente)

Para uso normal de estudiante (materiales nuevos de la semana) sobra ampliamente. Si querés procesar una materia entera de un saque, el sistema pausará automáticamente cuando llegue al rate limit.

El log te muestra cuántos PDFs te quedan en la cuota diaria:
```
Palabras: 2,341 | PDFs restantes hoy (aprox): ~42
```

Verificá tus límites actuales en: https://console.groq.com → Settings → Limits

### Cambiar a Anthropic (pago, sin límites diarios)
```cmd
set PROVIDER=anthropic
set ANTHROPIC_API_KEY=sk-ant-tu-key-aqui
```

### Instalar dependencia de Groq
```cmd
pip install groq
```

---

## 💰 Costos estimados (solo si usás Anthropic)

| Documentos/mes | Costo estimado |
|----------------|----------------|
| 20 docs de ~10 páginas | ~$0.10 |
| 50 docs de ~20 páginas | ~$0.50 |
| 100 docs de ~30 páginas | ~$1.50 |

Con Groq el costo es $0.00.

---

## 🔧 Personalización

La forma más fácil de personalizar es usar `python tui.py` — secciones **Modelo** y **Prompt**.

### Cambiar modelo de IA
Desde el TUI → sección **Modelo** → seleccioná el modelo deseado → **Guardar**.

O editá `config.py`:
```python
MODEL = "claude-haiku-4-5-20251001"   # Anthropic — más rápido y económico
MODEL = "claude-sonnet-4-5"            # Anthropic — más detallado
GROQ_MODEL = "llama-3.1-8b-instant"   # Groq — más rápido, menor calidad
```

### Personalizar el prompt de resumen
Desde el TUI → sección **Prompt** → editá el texto → **Guardar**.

O editá `SUMMARY_PROMPT_TEMPLATE` en `config.py`.

### Cambiar frecuencia de ejecución
En `setup_scheduler.bat`, cambiar `/d SUN` por:
- `/d MON` → lunes
- `/d MON,WED,FRI` → lunes, miércoles y viernes
- `/sc DAILY` → todos los días

---

## 🐛 Solución de problemas

**Docker: "failed to connect to docker API"**
→ Docker Desktop no está abierto. Abrilo y esperá a que el ícono de la ballena quede estático en la barra de tareas.

**Docker: "Acceso denegado" al crear processed_files.json**
→ Correr en CMD como administrador: `echo {} > processed_files.json`

**"ANTHROPIC_API_KEY no configurada"**
→ Verificar que el `.env` tenga la key correcta

**"NOTION_TOKEN no configurado"**
→ Verificar que el `.env` tenga el token correcto

**"La carpeta de documentos no existe"**
→ Con Docker: verificar que la carpeta `documentos/` exista junto al `docker-compose.yml`
→ Sin Docker: verificar la ruta `DOCUMENTS_ROOT` en `config.py`

**PDF sin texto extraído**
→ El PDF puede ser escaneado (imagen). Requeriría OCR (no incluido en esta versión).

**Rate limit de la API**
→ El sistema reintenta automáticamente. Si persiste, verificar el plan en console.groq.com

**Ver logs detallados:**
```
logs/summarizer.log
```

---

## 📋 Archivos del proyecto

```
Bot para facu/
├── Dockerfile               ← Imagen Docker del proyecto
├── docker-compose.yml       ← Configuración Docker (para desarrollo)
├── requirements.txt         ← Dependencias Python
├── main.py                  ← Script principal (CLI)
├── tui.py                   ← Interfaz gráfica TUI (ejecutar este)
├── config.py                ← Configuración central
├── .env                     ← Tus API keys (NO subir a GitHub)
├── .env.example             ← Plantilla del .env (sí subir)
├── .gitignore
├── README.md
├── install.bat              ← Instala dependencias (sin Docker)
├── setup_scheduler.bat      ← Configura tarea automática (sin Docker)
├── processed_files.json     ← Generado automáticamente
├── logs/
│   └── summarizer.log       ← Generado automáticamente
└── src/
    ├── ai_client.py         ← Comunica con Groq o Anthropic
    ├── campus_downloader.py ← Descarga desde el campus UNO
    ├── extractor.py         ← Lee PDFs y Word
    ├── notion_writer.py     ← Guarda resúmenes en Notion
    └── tracker.py           ← Registro de archivos procesados
```

---

## 🚀 Funcionalidades — v1.0.0

### Implementadas
- **Descarga automática del campus** — Se loguea al campus virtual de UNO (Moodle) con Playwright y descarga PDFs y DOCX nuevos de todos tus cursos
- **Descarga selectiva por materia** — `campus_downloader.py --materia "Álgebra" --año 2026 --dest C:\Carpeta` descarga solo el archivo más reciente de esa materia, reconociendo el formato de nombre `01017-Álgebra (1C2026)`
- **Extracción de texto** — Lee PDFs (pdfplumber) y archivos Word (.docx), incluyendo texto en tablas
- **Resumen con IA** — Genera resúmenes estructurados con técnica Feynman: Tema Central, Conceptos Clave, Desarrollo, Conexiones, Preguntas de Examen y tips de estudio
- **Soporte multi-proveedor** — Groq gratuito (`llama-3.3-70b-versatile`) o Anthropic Claude Haiku, configurable con `PROVIDER=groq/anthropic`
- **Estimado de cuota diaria** — Con Groq muestra cuántos PDFs te quedan en la cuota de 100k tokens/día; con Anthropic muestra el costo en USD
- **Guardado en Notion** — Crea páginas en una base de datos Notion con propiedades (Nombre, Materia, Fecha, Estado) y el resumen como contenido. Maneja bloques largos (+2000 chars) automáticamente
- **Anti-duplicados** — Verifica en Notion y en el registro local antes de procesar, evitando resumir dos veces el mismo archivo
- **Manejo de documentos largos** — Divide documentos extensos en chunks con superposición del 10%, resume por partes y consolida en un único resumen final
- **Reintentos automáticos** — Manejo de rate limits (429) con backoff para Groq y Anthropic
- **Tracking con hash MD5** — Detecta si un archivo ya procesado fue modificado y lo reprocesa
- **Credenciales seguras** — Variables de entorno via `.env` (python-dotenv), nunca hardcodeadas
- **CLI completo** — `--dry-run`, `--reset`, `--subject`, `--skip-download`, `--download-only`
- **Ejecución programada** — `setup_scheduler.bat` configura una tarea en Windows Task Scheduler

- **Interfaz TUI** — `python tui.py` abre un panel de configuración visual con 6 secciones: Estado, Proveedor, Modelo, Keys, Prompt y Ejecutar. Muestra límites y cuota de cada modelo en tiempo real. Ejecuta el procesamiento con log visible.