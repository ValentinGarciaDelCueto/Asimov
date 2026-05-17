@echo off
REM ============================================================
REM  setup_scheduler.bat
REM  Configura el Programador de Tareas de Windows para ejecutar
REM  el resumidor automáticamente cada domingo a las 8:00 AM
REM
REM  INSTRUCCIONES:
REM  1. Editá las variables PROJECT_DIR y PYTHON_PATH abajo
REM  2. Ejecutá este script como Administrador (clic derecho → Ejecutar como administrador)
REM ============================================================

REM ── EDITÁ ESTAS DOS LÍNEAS ───────────────────────────────────
set PROJECT_DIR=C:\Users\TuNombre\asimov
set PYTHON_PATH=C:\Users\TuNombre\AppData\Local\Programs\Python\Python311\python.exe
REM ─────────────────────────────────────────────────────────────

set TASK_NAME=Asimov

echo.
echo Configurando tarea programada: %TASK_NAME%
echo Carpeta del proyecto: %PROJECT_DIR%
echo Python: %PYTHON_PATH%
echo.

REM Eliminar tarea anterior si existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Crear la tarea: cada domingo a las 08:00
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON_PATH%\" \"%PROJECT_DIR%\main.py\"" ^
  /sc WEEKLY ^
  /d SUN ^
  /st 08:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Tarea creada exitosamente.
    echo      Se ejecutara cada domingo a las 08:00 AM.
    echo.
    echo Para verificar: Abre "Programador de tareas" y busca "%TASK_NAME%"
    echo Para ejecutar manualmente: schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo [ERROR] No se pudo crear la tarea. 
    echo         Asegurate de ejecutar como Administrador.
)

pause
