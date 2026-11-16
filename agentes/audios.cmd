@echo off
rem Atajo: audios ...  (funciona desde cualquier carpeta)
set "PYTHONPATH=%~dp0.."
set "PYTHONIOENCODING=utf-8"
python -m agentes.audios %*
