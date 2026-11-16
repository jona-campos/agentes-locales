"""Agente 2: esqueleto de pruebas con un caso por función pública, que falla hasta que se complete (TDD)."""
import argparse
import ast
import json
import os
import re
import sys
import unicodedata

from agentes.modelo import cliente_ollama, tapar

PENDIENTE = "pendiente"
ESQUEMA = {"type": "object", "required": ["casos"], "properties": {"casos": {"type": "array", "items": {
    "type": "object", "required": ["miembro", "casos"],
    "properties": {"miembro": {"type": "string"}, "casos": {"type": "array", "items": {"type": "string"}}}}}}}


def publicos_python(fuente):
    """Funciones y métodos públicos, en el orden del archivo: ["total", "Caja.abrir"]."""
    try:
        arbol = ast.parse(fuente)
    except SyntaxError as e:
        raise ValueError(f"el archivo no es Python válido: {e}")
    funcion = (ast.FunctionDef, ast.AsyncFunctionDef)
    nombres = []
    for nodo in arbol.body:
        if nodo.name.startswith("_") if isinstance(nodo, (*funcion, ast.ClassDef)) else True:
            continue
        if isinstance(nodo, ast.ClassDef):
            nombres += [f"{nodo.name}.{m.name}" for m in nodo.body
                        if isinstance(m, funcion) and not m.name.startswith("_")]
        else:
            nombres.append(nodo.name)
    return nombres


def prompt(miembros, fuente):
    if miembros is None:
        pedido = ('Lista las funciones, clases y métodos públicos de este archivo Dart (los que no empiezan con "_"). '
                  'Usa "Clase.metodo" para los métodos.')
    else:
        pedido = "Miembros públicos: " + ", ".join(miembros) + "."
    return f"""{pedido}
Para cada uno propón hasta 3 casos de prueba: el caso normal y los límites que se ven en el código (vacío, cero, error).
Cada caso es una frase corta en español que dice la conducta esperada, por ejemplo "devuelve 0 con la lista vacía".
No escribas código ni inventes miembros que no estén en el archivo.

Archivo:
{fuente}
"""


def casos(miembros, fuente, modelo):
    """{miembro: [casos]}. Con miembros=None (Dart) los propone el modelo y se comprueban contra el archivo."""
    basico = {m: [PENDIENTE] for m in miembros or []}
    if not modelo:
        return basico
    try:
        propuestos = json.loads(modelo(prompt(miembros, tapar(fuente))))["casos"]
        resultado = {}
        for p in propuestos:
            nombre = p["miembro"]
            partes = nombre.split(".")
            # el modelo no decide qué existe: en Python manda ast; en Dart el nombre tiene que salir en el archivo
            existe = nombre in basico if miembros is not None else (
                not any(x.startswith("_") for x in partes)
                and all(re.search(rf"\b{re.escape(x)}\b", fuente) for x in partes))
            if existe:
                resultado[nombre] = [str(c).strip() for c in p["casos"] if str(c).strip()][:3] or [PENDIENTE]
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        return basico
    return {**basico, **resultado} if miembros is None else {m: resultado.get(m, [PENDIENTE]) for m in miembros}


def _identificador(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")


def esqueleto_python(modulo, casos_por_miembro):
    lineas = ["import unittest", "", f"import {modulo}  # noqa: F401", "", "",
              f"class Test{_identificador(modulo).title().replace('_', '')}(unittest.TestCase):"]
    usados = set()
    for miembro, lista in casos_por_miembro.items():
        for caso in lista:
            nombre = "test_" + _identificador(miembro if caso == PENDIENTE else f"{miembro} {caso}")
            while nombre in usados:
                nombre += "_bis"
            usados.add(nombre)
            lineas += [f"    def {nombre}(self):", f"        # {miembro}: {caso}", f'        self.fail("{PENDIENTE}")', ""]
    return "\n".join(lineas + ["", 'if __name__ == "__main__":', "    unittest.main()", ""])


def esqueleto_dart(casos_por_miembro, importe):
    def comillas(t):
        return t.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")
    lineas = ["import 'package:flutter_test/flutter_test.dart';", f"import '{importe}';", "", "void main() {"]
    for miembro, lista in casos_por_miembro.items():
        lineas.append(f"  group('{comillas(miembro)}', () {{")
        for caso in lista:
            lineas += [f"    test('{comillas(caso)}', () {{", f"      fail('{PENDIENTE}');", "    });"]
        lineas.append("  });")
    return "\n".join(lineas + ["}", ""])


def destino_dart(fuente):
    """(archivo de pruebas, import). Si está en lib/ de un paquete va a test/ con import de paquete."""
    fuente = os.path.abspath(fuente)
    carpeta = os.path.dirname(fuente)
    while not os.path.exists(os.path.join(carpeta, "pubspec.yaml")) and os.path.dirname(carpeta) != carpeta:
        carpeta = os.path.dirname(carpeta)
    relativa = os.path.relpath(fuente, os.path.join(carpeta, "lib"))
    pubspec = os.path.join(carpeta, "pubspec.yaml")
    if os.path.exists(pubspec) and not relativa.startswith(".."):
        with open(pubspec, encoding="utf-8") as f:
            paquete = re.search(r"(?m)^name:\s*(\S+)", f.read()).group(1)
        return (os.path.join(carpeta, "test", relativa[:-5] + "_test.dart"),
                f"package:{paquete}/{relativa.replace(os.sep, '/')}")
    return fuente[:-5] + "_test.dart", os.path.basename(fuente)


def main(argv=None):
    p = argparse.ArgumentParser(prog="pruebas", description="Esqueleto de pruebas para un archivo Python o Dart.")
    sub = p.add_subparsers(dest="orden", required=True)
    e = sub.add_parser("esqueleto")
    e.add_argument("archivo")
    e.add_argument("--sin-ia", action="store_true", help="solo Python: un caso por función, sin proponer casos")
    e.add_argument("--modelo", default="qwen2.5-coder:7b")
    a = p.parse_args(argv)
    try:
        with open(a.archivo, encoding="utf-8") as f:
            fuente = f.read()
    except OSError as error:
        sys.exit(f"No pude leer {a.archivo}: {error}")
    modelo = None if a.sin_ia else cliente_ollama(a.modelo, ESQUEMA)
    nombre, extension = os.path.splitext(os.path.basename(a.archivo))
    if extension == ".py":
        try:
            miembros = publicos_python(fuente)
        except ValueError as error:
            sys.exit(str(error))
        destino = os.path.join(os.path.dirname(os.path.abspath(a.archivo)), f"test_{nombre}.py")
        codigo = esqueleto_python(nombre, casos(miembros, fuente, modelo))
    elif extension == ".dart":
        if not modelo:
            sys.exit("En Dart los miembros los saca el modelo: quita --sin-ia.")
        destino, importe = destino_dart(a.archivo)
        miembros = casos(None, fuente, modelo)
        codigo = esqueleto_dart(miembros, importe)
    else:
        sys.exit("Solo sé hacer esqueletos para .py y .dart")
    if not miembros:
        sys.exit("No encontré funciones públicas (o el modelo no respondió con el formato pedido).")
    if os.path.exists(destino):
        sys.exit(f"Ya existe {destino}; no lo piso.")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(codigo)
    print(f"Escribí {destino} ({codigo.count('fail(')} pruebas pendientes)")
    return 0


if __name__ == "__main__":
    main()
