@echo off
REM ============================================================
REM  install.bat — Instala todas las dependencias del proyecto
REM  Ejecutá este script UNA SOLA VEZ para configurar el entorno
REM ============================================================

echo.
echo ====================================================
echo  Instalando dependencias de Academic Summarizer
echo ====================================================
echo.

REM Verificar que Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python no encontrado.
    echo         Instalalo desde https://python.org/downloads
    echo         Asegurate de marcar "Add Python to PATH" durante la instalacion
    pause
    exit /b 1
)

echo [OK] Python encontrado.
echo.

REM Instalar dependencias
echo Instalando librerias...
pip install anthropic groq pdfplumber python-docx notion-client playwright python-dotenv textual

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Dependencias instaladas correctamente.
) else (
    echo.
    echo [ERROR] Fallo al instalar dependencias.
    pause
    exit /b 1
)

echo.
echo Instalando navegador para Playwright...
playwright install chromium

echo.
echo ====================================================
echo  Configuracion pendiente:
echo ====================================================
echo.
echo  1. Copia el archivo .env.example como .env:
echo     copy .env.example .env
echo.
echo  2. Abri .env con el Bloc de notas y completá:
echo     - GROQ_API_KEY     (gratis en console.groq.com)
echo     - CAMPUS_USER      (usuario del campus UNO)
echo     - CAMPUS_PASS      (contraseña del campus UNO)
echo     - NOTION_TOKEN     (token de tu integración)
echo     - NOTION_DATABASE_ID (ID de tu base de datos)
echo     - DOCUMENTS_ROOT   (carpeta con tus PDFs/Word)
echo.
echo  3. Abrí la interfaz gráfica con:
echo     python tui.py
echo.
echo     (o usá la CLI directamente):
echo     python main.py --dry-run
echo.
echo  4. Cuando funcione, configurá el scheduler:
echo     Ejecutá setup_scheduler.bat como Administrador
echo.
echo ====================================================
pause
