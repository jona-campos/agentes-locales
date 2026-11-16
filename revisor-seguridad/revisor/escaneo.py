"""Ejecuta los cuatro escáneres en paralelo, sin red, y devuelve sus hallazgos normalizados."""
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from revisor import hallazgos as h

PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGLAS = os.path.join(PROYECTO, "reglas", "semgrep-rules")
CONFIGS = ["python", "javascript", os.path.join("generic", "secrets")]
EXCLUIR = [".revisor", ".venv", "venv", "node_modules", ".git", "build", "dist", ".svelte-kit", ".dart_tool",
           "ephemeral", ".data", ".pytest_cache", "coverage", "Pods", ".gradle"]


def config_gitleaks(excluir):
    """Configuración que mantiene las reglas de gitleaks y salta las carpetas generadas (acepta barra normal e invertida)."""
    barra = r"[/\\\\]"  # clase regex: "/" o "\"
    rutas = "\n".join(f"  '''(^|{barra}){re.escape(d)}({barra}|$)'''," for d in excluir)
    return f"[extend]\nuseDefault = true\n\n[allowlist]\npaths = [\n{rutas}\n]\n"


def _buscar(nombre):
    winget = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", nombre + ".exe")
    return shutil.which(nombre) or winget


def rutas_por_defecto():
    scripts = os.path.dirname(sys.executable)  # semgrep y bandit viven en el mismo venv que revisor
    return {"gitleaks": _buscar("gitleaks"), "osv-scanner": _buscar("osv-scanner"),
            "semgrep": os.path.join(scripts, "semgrep.exe"), "bandit": os.path.join(scripts, "bandit.exe")}


def _tareas(ruta, tmp, r):
    """herramienta -> (comando, archivo de salida o None si es stdout, códigos de salida aceptados, lector)."""
    sale = lambda n: os.path.join(tmp, n + ".json")
    config = os.path.join(tmp, "gitleaks.toml")
    with open(config, "w", encoding="utf-8") as f:
        f.write(config_gitleaks(EXCLUIR))
    return {
        "gitleaks": ([r["gitleaks"], "dir", ruta, "--report-format", "json", "--report-path", sale("gitleaks"),
                      "--no-banner", "--exit-code", "0", "--redact", "--log-level", "error", "--config", config],
                     sale("gitleaks"), {0}, h.desde_gitleaks),
        "bandit": ([r["bandit"], "-r", ruta, "-f", "json", "-o", sale("bandit"), "-q",
                    "-s", "B101",  # assert: solo es riesgo con python -O y en pruebas es ruido
                    "-x", ",".join(f"*/{d}/*" for d in EXCLUIR)], sale("bandit"), {0, 1}, h.desde_bandit),
        "semgrep": ([r["semgrep"], "scan", "--metrics=off", "--disable-version-check", "--json", "-o", sale("semgrep"),
                     *[a for c in CONFIGS for a in ("--config", os.path.join(REGLAS, c))],
                     *[a for d in EXCLUIR for a in ("--exclude", d)], ruta], sale("semgrep"), {0}, h.desde_semgrep),
        # --offline: sin red ni resolución de dependencias transitivas; usa la base local ya descargada
        "osv-scanner": ([r["osv-scanner"], "scan", "source", "--offline", "--format", "json", "-r", ruta],
                        None, {0, 1}, h.desde_osv),
    }


def _correr(nombre, comando, salida, aceptados, lector, ruta):
    if not os.path.isfile(comando[0]):
        return [], f"{nombre}: no se encontró {comando[0]}"
    p = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1"})
    if nombre == "osv-scanner" and p.returncode == 128:
        return [], None  # 128 = no hay archivos de dependencias que revisar
    if p.returncode not in aceptados:
        ultima = (p.stderr.strip().splitlines() or ["sin mensaje"])[-1]
        return [], f"{nombre}: terminó con código {p.returncode}: {ultima[:200]}"
    try:
        if salida:
            with open(salida, encoding="utf-8") as f:
                datos = json.load(f)
        else:
            datos = json.loads(p.stdout)
        return lector(datos, ruta), None
    except (OSError, ValueError, KeyError) as e:
        return [], f"{nombre}: no se pudo leer su salida ({e})"


def ejecutar(ruta, tmp, rutas=None):
    """Devuelve (hallazgos, avisos). Si un escáner falla, se anota el aviso y siguen los demás."""
    r = {**rutas_por_defecto(), **(rutas or {})}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futuros = [pool.submit(_correr, n, *t, ruta) for n, t in _tareas(ruta, tmp, r).items()]
        resultados = [f.result() for f in futuros]
    return [x for hs, _ in resultados for x in hs], [a for _, a in resultados if a]
