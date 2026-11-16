@echo off
rem Atajo: revisor escanear <ruta>  (funciona desde cualquier carpeta)
set "PYTHONPATH=%~dp0"
set "PYTHONIOENCODING=utf-8"
"%~dp0.venv\Scripts\python.exe" -m revisor %*
