"""revisor actualizar: refresca las reglas de Semgrep y las bases de osv-scanner. Es la única orden que usa internet.

Solo se descargan datos públicos; a osv.dev no se manda ningún nombre de paquete del usuario: los manifiestos
de abajo son de ejemplo y sirven para que osv-scanner sepa qué ecosistemas bajar.
"""
import json
import os
import subprocess
import tempfile

from revisor import escaneo

MANIFIESTOS = {
    # osv-scanner solo reconoce el ecosistema npm si la entrada tiene "resolved" e "integrity"
    "package-lock.json": json.dumps({"name": "x", "version": "1.0.0", "lockfileVersion": 3, "packages": {
        "": {"name": "x", "version": "1.0.0", "dependencies": {"left-pad": "1.3.0"}},
        "node_modules/left-pad": {
            "version": "1.3.0", "resolved": "https://registry.npmjs.org/left-pad/-/left-pad-1.3.0.tgz",
            "integrity": "sha512-XI5MPzVNApjAyhQzphX8BkmKsKUxD4LdyK24iZeQGinBN9yTQT3bFlCBy/aVx2HrNcqQGsdot8ghrjyrvMCoEA=="}}}),
    "requirements.txt": "requests==2.32.0\n",
    "pubspec.lock": 'packages:\n  path:\n    dependency: "direct main"\n    description:\n'
                    '      name: path\n      url: "https://pub.dev"\n    source: hosted\n    version: "1.9.0"\n'
                    'sdks:\n  dart: ">=3.0.0 <4.0.0"\n',
}


def correr(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stderr or p.stdout).strip()


def actualizar(ejecutar=correr, rutas=None):
    """Devuelve la lista de avisos (vacía si todo salió bien). Un paso que falla no frena al otro."""
    r = {"git": "git", "osv-scanner": escaneo.rutas_por_defecto()["osv-scanner"], **(rutas or {})}
    avisos = []
    codigo, salida = ejecutar([r["git"], "-C", escaneo.REGLAS, "pull", "--ff-only"])
    if codigo:
        avisos.append(f"reglas de Semgrep: git pull falló ({salida[-200:]})")
    with tempfile.TemporaryDirectory() as tmp:
        for nombre, texto in MANIFIESTOS.items():
            with open(os.path.join(tmp, nombre), "w", encoding="utf-8") as f:
                f.write(texto)
        # código 1 = encontró vulnerabilidades en los paquetes de ejemplo: la descarga sí se hizo
        codigo, salida = ejecutar([r["osv-scanner"], "scan", "source", "--offline-vulnerabilities",
                                   "--download-offline-databases", "--format", "json", "-r", tmp])
        if codigo not in (0, 1):
            avisos.append(f"bases de osv-scanner: terminó con código {codigo} ({salida[-200:]})")
    return avisos
