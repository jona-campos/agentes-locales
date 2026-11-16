@echo off
rem Atajo: commit ...  (funciona desde cualquier carpeta)
set "PYTHONPATH=%~dp0.."
set "PYTHONIOENCODING=utf-8"
python -m agentes.commit %*
