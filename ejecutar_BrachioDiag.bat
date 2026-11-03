@echo off
title BrachioDiag - App de Escritorio (Angelica Serracin)

:: 1. Buscar Pythonw.exe para iniciar en modo aplicacion de escritorio (sin ventana CMD)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" "%~dp0BrachioDiag.pyw"
    exit /b 0
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" "%~dp0BrachioDiag.pyw"
    exit /b 0
)

if exist "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe" "%~dp0BrachioDiag.pyw"
    exit /b 0
)

:: 2. Buscar lanzador pyw o pythonw en PATH
where pyw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pyw "%~dp0BrachioDiag.pyw"
    exit /b 0
)

where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw "%~dp0BrachioDiag.pyw"
    exit /b 0
)

:: 3. Si solo esta python estándar en consola
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%~dp0BrachioDiag.pyw"
    exit /b 0
)

python "%~dp0BrachioDiag.pyw"

