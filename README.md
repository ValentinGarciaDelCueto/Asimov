# 📚 Academic Summarizer

Sistema automático que lee tus documentos universitarios (PDF y Word), los resume con IA y guarda los resultados en Notion, organizado por materia.

---

## ⚡ Instalación rápida (4 pasos)

### 1. Instalar dependencias
```
install.bat
```
O manualmente:
```cmd
pip install anthropic groq pdfplumber python-docx notion-client playwright python-dotenv
playwright install chromium
```

### 2. Crear el archivo .env
```cmd
copy .env.example .env
```
Abrí `.env` con el Bloc de notas y completá tus valores:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
CAMPUS_USER=tu_usuario
CAMPUS_PASS=tu_contraseña
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DOCUMENTS_ROOT=C:\Users\TuNombre\Documentos\Universidad
```
El archivo `.env` **nunca se sube a GitHub** — ya está en `.gitignore`.

### 3. Obtener las API keys
- **Groq (gratis):** https://console.groq.com → API Keys
- **Notion:** https://www.notion.so/my-integrations → New Integration → copiar token
- **Anthropic (solo si usás `PROVIDER=anthropic`):** https://console.anthropic.com → API Keys

### 4. Probar
```cmd
python main.py --dry-run
```
Si muestra los archivos sin errores, todo está listo.

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

### Cambiar modelo de IA (config.py)
```python
# Más barato, rápido
MODEL = "claude-haiku-4-5-20251001"

# Más detallado (x6 más caro)
MODEL = "claude-sonnet-4-6"
```

### Personalizar el formato del resumen (config.py)
Editá `SUMMARY_PROMPT_TEMPLATE` para cambiar la estructura del resumen generado.

### Cambiar frecuencia de ejecución
En `setup_scheduler.bat`, cambiar `/d SUN` por:
- `/d MON` → lunes
- `/d MON,WED,FRI` → lunes, miércoles y viernes
- `/sc DAILY` → todos los días

---

## 🐛 Solución de problemas

**"ANTHROPIC_API_KEY no configurada"**
→ Ejecutar `set ANTHROPIC_API_KEY=sk-ant-...` en la misma terminal

**"NOTION_TOKEN no configurado"**
→ Ejecutar `set NOTION_TOKEN=secret_...` en la misma terminal

**"La carpeta de documentos no existe"**
→ Verificar la ruta `DOCUMENTS_ROOT` en `config.py`

**PDF sin texto extraído**
→ El PDF puede ser escaneado (imagen). Requeriría OCR (no incluido en esta versión).

**Rate limit de la API**
→ El sistema reintenta automáticamente. Si persiste, verificar el plan en console.anthropic.com

**Ver logs detallados:**
```
logs/summarizer.log
```

---

## 📋 Archivos del proyecto

```
Bot para facu/
├── main.py                  ← Script principal (ejecutar este)
├── config.py                ← Configuración (editá este)
├── .env                     ← Tus API keys (NO subir a GitHub)
├── .env.example             ← Plantilla del .env (sí subir)
├── .gitignore
├── README.md
├── install.bat              ← Instala dependencias
├── setup_scheduler.bat      ← Configura tarea automática
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

### Ideas para próximas versiones
- OCR para PDFs escaneados (imágenes)
- Resumen comparativo entre parciales de distintos años
- Notificación por WhatsApp/email cuando hay material nuevo en el campus
- Modo interactivo para elegir materia sin escribir comandos
