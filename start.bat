@echo off
chcp 65001 >nul
title Aegis DLP - Launcher Local (Sin Docker)
cd /d "%~dp0"

echo =========================================================================
echo       Iniciando Aegis DLP en Windows (Sin Docker) ...
echo =========================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*

pause
