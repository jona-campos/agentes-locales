"""Agente 1: propone un mensaje Conventional Commits desde lo preparado y arma el changelog desde git log."""
import argparse
import json
import re
import subprocess
import sys

from agentes.modelo import cliente_ollama, tapar

TIPOS = {"feat": "Novedades", "fix": "Correcciones", "perf": "Rendimiento", "refactor": "Refactorizaciones",
         "docs": "Documentación", "test": "Pruebas", "build": "Compilación", "ci": "Integración continua",
         "style": "Estilo", "chore": "Mantenimiento", "revert": "Reversiones"}
ESQUEMA = {"type": "object", "required": ["tipo", "resumen"],
           "properties": {"tipo": {"type": "string", "enum": list(TIPOS)}, "ambito": {"type": "string"},
                          "resumen": {"type": "string"}, "cuerpo": {"type": "string"}}}
MAX_TITULO = 72


def recortar_diff(diff, por_archivo=80, total=400):
    """Deja el principio de cada archivo para que el diff quepa en el contexto del modelo."""
    salida = []
    for parte in re.split(r"(?m)^(?=diff --git )", diff):
        lineas = parte.splitlines(keepends=True)
        if len(lineas) > por_archivo:
            lineas = lineas[:por_archivo] + [f"... ({len(lineas) - por_archivo} líneas omitidas)\n"]
        salida += lineas
    if len(salida) > total:
        salida = salida[:total] + [f"... ({len(salida) - total} líneas omitidas)\n"]
    return "".join(salida)


def interpretar(respuesta):
    """Valida el JSON del modelo y devuelve el mensaje; ValueError si no sirve."""
    try:
        d = json.loads(respuesta)
        tipo, resumen = d["tipo"], d["resumen"].strip().rstrip(".")
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"respuesta sin el formato pedido: {e}")
    if tipo not in TIPOS or not resumen or "\n" in resumen:
        raise ValueError("tipo desconocido o resumen vacío")
    ambito = str(d.get("ambito") or "").strip()
    titulo = f"{tipo}({ambito}): {resumen}" if ambito else f"{tipo}: {resumen}"
    if len(titulo) > MAX_TITULO:
        raise ValueError(f"título de {len(titulo)} caracteres, el tope es {MAX_TITULO}")
    cuerpo = str(d.get("cuerpo") or "").strip()
    return f"{titulo}\n\n{cuerpo}" if cuerpo else titulo


def prompt(diff, stat, idioma):
    return f"""Escribe el mensaje de commit para este cambio, en formato Conventional Commits.

Reglas:
- "tipo": feat (función nueva), fix (corrige un error), refactor (misma conducta, otro código), docs, test, perf, build, ci, style o chore.
- "ambito": módulo o carpeta afectada, una palabra en minúsculas; vacío si el cambio toca varios.
- "resumen": qué cambia, en {idioma}, en imperativo, sin punto final, máximo 50 caracteres.
- "cuerpo": opcional, una o dos frases con el porqué si el diff lo deja claro. No inventes motivos.
- No copies claves, tokens ni contraseñas.

Archivos:
{stat}

Diff:
{diff}
"""


def tipo_seguro(diff):
    """"docs" o "test" si todos los archivos del diff lo son; None si hay que preguntarle al modelo."""
    archivos = re.findall(r"(?m)^diff --git a/.+ b/(.+)$", diff)
    if archivos and all(a.lower().endswith((".md", ".txt", ".rst")) for a in archivos):
        return "docs"
    if archivos and all(re.search(r"(^|/)tests?/|_test\.|(^|/)test_|\.(test|spec)\.", a) for a in archivos):
        return "test"
    return None


def sugerir(diff, stat, modelo, idioma="español"):
    """Mensaje propuesto, o None si el modelo no da uno válido en dos intentos."""
    texto = prompt(tapar(recortar_diff(diff)), stat, idioma)
    fijo = tipo_seguro(diff)  # el modelo llamaba "fix" o "refactor" a commits que solo tocaban documentos
    for _ in range(2):
        try:
            mensaje = interpretar(modelo(texto))
            return re.sub(r"^\w+", fijo, mensaje, count=1) if fijo else mensaje
        except ValueError as error:
            # con temperatura 0 repetir el mismo prompt da la misma respuesta: hay que decirle qué falló
            texto += f"\nTu respuesta anterior no sirvió: {error}. Corrígela; el resumen debe ser más corto.\n"
    return None


_CONVENCIONAL = re.compile(r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$")


def changelog(titulos):
    """Markdown con los commits agrupados por tipo; los que no siguen el formato van a "Otros"."""
    grupos = {}
    for t in titulos:
        m = _CONVENCIONAL.match(t)
        if m and m.group(1) in TIPOS:
            tipo, ambito, rompe, resumen = m.groups()
            linea = (f"**{ambito}:** " if ambito else "") + resumen + (" (cambio incompatible)" if rompe else "")
            grupos.setdefault(TIPOS[tipo], []).append(linea)
        elif not t.startswith("Merge "):
            grupos.setdefault("Otros", []).append(t)
    orden = [*TIPOS.values(), "Otros"]
    return "\n\n".join(f"## {g}\n\n" + "\n".join(f"- {x}" for x in grupos[g]) for g in orden if g in grupos) + "\n"


def _git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(r.stderr.strip() or f"git {args[0]} falló")
    return r.stdout


def main(argv=None):
    p = argparse.ArgumentParser(prog="commit", description="Mensaje de commit y changelog con un modelo local.")
    sub = p.add_subparsers(dest="orden", required=True)
    s = sub.add_parser("sugerir", help="propone un mensaje para lo preparado (git add); no hace el commit")
    s.add_argument("--idioma", default="español")
    s.add_argument("--modelo", default="qwen2.5-coder:7b")
    c = sub.add_parser("changelog", help="agrupa los commits por tipo")
    c.add_argument("rango", nargs="?", default="HEAD", help="por ejemplo v1.0..HEAD")
    a = p.parse_args(argv)
    if a.orden == "changelog":
        print(changelog(_git("log", "--pretty=%s", a.rango).splitlines()), end="")
        return
    diff = _git("diff", "--staged")
    if not diff.strip():
        sys.exit("No hay nada preparado. Usa git add primero.")
    try:
        mensaje = sugerir(diff, _git("diff", "--staged", "--stat"), cliente_ollama(a.modelo, ESQUEMA), a.idioma)
    except OSError as e:
        sys.exit(f"No pude hablar con Ollama ({e}). ¿Está abierto?")
    if not mensaje:
        sys.exit("El modelo no dio un mensaje válido en dos intentos.")
    print(mensaje)


if __name__ == "__main__":
    main()
