"""Agente 4: agrupa las líneas de un log en plantillas y pide al modelo que explique los errores y las raras."""
import argparse
import re
import sys
from collections import namedtuple

from agentes.modelo import cliente_ollama, tapar

Grupo = namedtuple("Grupo", "plantilla veces linea ejemplo")

# shortcut: plantillas con expresiones regulares en vez de Drain3; si un mismo mensaje sale partido
# en muchas plantillas (palabras variables, no números), pasar a Drain3.
_VARIABLE = re.compile(r"""
    \d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:?\d\d)?   # fecha y hora
  | \b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b            # UUID
  | \b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b                                 # IP con puerto opcional
  | \b0x[0-9a-fA-F]+\b                                                   # hexadecimal
  | \b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{8,}\b                    # hash o id en hexadecimal
  | \b\d+(?:[.,]\d+)?\b                                                  # números
""", re.X)
_ERROR = re.compile(r"error|exception|fail|fatal|traceback|panic|critical|denied|timeout|refused", re.I)


def plantilla(linea):
    return " ".join(_VARIABLE.sub("<*>", linea).split())


def agrupar(lineas):
    """Una entrada por plantilla, con cuántas veces sale y su primer ejemplo (número de línea desde 1)."""
    grupos = {}
    for n, linea in enumerate(lineas, 1):
        linea = linea.rstrip("\r\n")
        if not linea.strip():
            continue
        p = plantilla(linea)
        g = grupos.get(p)
        grupos[p] = g._replace(veces=g.veces + 1) if g else Grupo(p, 1, n, linea)
    return _fusionar(list(grupos.values()))


def _fusionar(grupos, minimo=3):
    """Junta las plantillas que solo cambian en una palabra (nombres de paquete, rutas) si hay 3 o más variantes."""
    # shortcut: una sola pasada y una sola palabra variable por plantilla; para más, Drain3.
    # Los errores no se juntan: "conexión rechazada" y "conexión cerrada" son problemas distintos.
    def claves(g):
        t = g.plantilla.split()
        return [" ".join(t[:i] + ["<*>"] + t[i + 1:]) for i in range(len(t)) if t[i] != "<*>"]
    variantes = {}
    for g in grupos:
        if not _ERROR.search(g.plantilla):
            for c in claves(g):
                variantes[c] = variantes.get(c, 0) + 1
    juntos = {}
    for g in grupos:
        destino = g.plantilla
        if not _ERROR.search(destino):
            destino = max(claves(g), key=lambda c: variantes[c], default=destino)
            if variantes.get(destino, 0) < minimo:
                destino = g.plantilla
        j = juntos.get(destino)
        if not j:
            juntos[destino] = g._replace(plantilla=destino)
        else:
            primero = min(j, g, key=lambda x: x.linea)
            juntos[destino] = Grupo(destino, j.veces + g.veces, primero.linea, primero.ejemplo)
    return list(juntos.values())


def elegir(grupos, tope=30):
    """Lo que vale la pena explicar: primero los errores (los más repetidos antes) y luego las plantillas más raras."""
    errores = sorted((g for g in grupos if _ERROR.search(g.plantilla)), key=lambda g: -g.veces)
    raras = sorted((g for g in grupos if not _ERROR.search(g.plantilla)), key=lambda g: g.veces)
    return (errores + raras)[:tope]


def _tabla(grupos):
    def celda(t):
        return t[:200].replace("|", "\\|")
    filas = "\n".join(f"| {g.veces} | {g.linea} | {celda(g.plantilla)} | {celda(g.ejemplo)} |" for g in grupos)
    return "| Veces | Primera línea | Plantilla | Ejemplo |\n|---|---|---|---|\n" + filas


def prompt(total, grupos, elegidos):
    lista = "\n".join(f"- {g.veces} veces, desde la línea {g.linea}: {g.ejemplo[:300]}" for g in elegidos)
    return f"""Eres quien revisa los registros de una aplicación. El log tiene {total} líneas que se agruparon en {len(grupos)} mensajes distintos.
Estos son los errores y los mensajes menos frecuentes, con cuántas veces sale cada uno y un ejemplo:

{lista}

Responde en español, en menos de 200 palabras:
1. Qué falla, citando el mensaje y la línea.
2. Causa probable, solo si el log la sugiere. Si no se puede saber, dilo.
3. Qué revisar primero.
No inventes datos que no estén arriba.
"""


def informe(lineas, modelo, tope=30):
    """Informe en Markdown. Con modelo=None sale solo la parte calculada, sin explicación."""
    grupos = agrupar(lineas)
    total = sum(g.veces for g in grupos)
    elegidos = elegir(grupos, tope)
    partes = [f"# Resumen del log\n\n{total} líneas, {len(grupos)} plantillas.",
              "## Errores y mensajes raros\n\n" + _tabla(elegidos),
              "## Más repetidas\n\n" + _tabla(sorted(grupos, key=lambda g: -g.veces)[:10])]
    if modelo:
        try:
            partes.insert(1, "## Explicación\n\n" + modelo(tapar(prompt(total, grupos, elegidos))).strip())
        except OSError as e:
            partes.insert(1, f"> El modelo no respondió ({e}); abajo va solo el conteo.")
    return tapar("\n\n".join(partes)) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(prog="logs", description="Resume un log con un modelo local.")
    sub = p.add_subparsers(dest="orden", required=True)
    r = sub.add_parser("resumir")
    r.add_argument("archivo")
    r.add_argument("--sin-ia", action="store_true", help="solo plantillas y conteo")
    r.add_argument("--modelo", default="qwen2.5-coder:7b")
    a = p.parse_args(argv)
    try:
        with open(a.archivo, encoding="utf-8", errors="replace") as f:
            print(informe(f, None if a.sin_ia else cliente_ollama(a.modelo)), end="")
    except FileNotFoundError:
        sys.exit(f"No existe {a.archivo}")


if __name__ == "__main__":
    main()
