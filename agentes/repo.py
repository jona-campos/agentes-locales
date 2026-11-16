"""Agente 3: búsqueda semántica local sobre un repositorio y respuestas que citan archivo y línea."""
import argparse
import math
import os
import sqlite3
import sys
from array import array
from collections import namedtuple

from agentes.modelo import EXCLUIR, cliente_embeddings, cliente_ollama, tapar

Resultado = namedtuple("Resultado", "archivo linea texto puntaje")
EXTENSIONES = {".py", ".dart", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".vue", ".java", ".kt", ".go", ".rs", ".c",
               ".h", ".cpp", ".cs", ".php", ".rb", ".sql", ".sh", ".ps1", ".html", ".css", ".md", ".yaml", ".yml"}
DOCUMENTOS = (".md", ".yaml", ".yml")
MAX_BYTES = 200_000  # más grande que esto suele ser generado o datos
# nomic-embed-text espera estos prefijos para distinguir documento de pregunta
PREFIJO_DOC, PREFIJO_PREGUNTA = "search_document: ", "search_query: "


def trocear(texto, lineas=60, solape=10):
    """[(línea inicial desde 1, texto)]. shortcut: corte por líneas fijas; si la búsqueda falla, cortar por funciones."""
    todas = texto.splitlines(keepends=True)
    trozos = []
    for i in range(0, len(todas), lineas - solape):
        trozo = "".join(todas[i:i + lineas])
        if trozo.strip():
            trozos.append((i + 1, trozo))
        if i + lineas >= len(todas):
            break
    return trozos


def _archivos(raiz):
    for carpeta, subcarpetas, nombres in os.walk(raiz):
        subcarpetas[:] = [d for d in subcarpetas if d not in EXCLUIR]
        for n in nombres:
            ruta = os.path.join(carpeta, n)
            if os.path.splitext(n)[1].lower() in EXTENSIONES and os.path.getsize(ruta) <= MAX_BYTES:
                yield os.path.relpath(ruta, raiz).replace(os.sep, "/"), ruta


def _normal(vector):
    largo = math.sqrt(sum(x * x for x in vector)) or 1.0
    return array("f", (x / largo for x in vector))


def _abrir(raiz, crear):
    carpeta = os.path.join(raiz, ".agentes")
    base = os.path.join(carpeta, "indice.db")
    if not crear and not os.path.exists(base):
        raise FileNotFoundError(f"No hay índice en {raiz}. Corre primero: repo indexar")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, ".gitignore"), "w") as f:
        f.write("*\n")  # el índice copia trozos de código: que no llegue a un commit
    db = sqlite3.connect(base)
    db.execute("CREATE TABLE IF NOT EXISTS archivos (ruta TEXT PRIMARY KEY, modificado INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS trozos (archivo TEXT, linea INTEGER, texto TEXT, vector BLOB)")
    return db


def indexar(raiz, embeber, avisar=lambda ruta: None):
    """Indexa lo nuevo o cambiado y quita lo borrado. Devuelve cuántos archivos se (re)indexaron."""
    raiz = str(raiz)
    db = _abrir(raiz, crear=True)
    previos = dict(db.execute("SELECT ruta, modificado FROM archivos"))
    vistos, hechos = set(), 0
    for relativa, ruta in _archivos(raiz):
        vistos.add(relativa)
        modificado = os.stat(ruta).st_mtime_ns
        if previos.get(relativa) == modificado:
            continue
        with open(ruta, encoding="utf-8", errors="replace") as f:
            trozos = trocear(f.read())
        avisar(relativa)
        db.execute("DELETE FROM trozos WHERE archivo = ?", (relativa,))
        for i in range(0, len(trozos), 16):
            lote = trozos[i:i + 16]
            vectores = embeber([PREFIJO_DOC + f"{relativa}\n{t[:6000]}" for _, t in lote])
            db.executemany("INSERT INTO trozos VALUES (?, ?, ?, ?)",
                           [(relativa, linea, t, _normal(v).tobytes()) for (linea, t), v in zip(lote, vectores)])
        db.execute("INSERT OR REPLACE INTO archivos VALUES (?, ?)", (relativa, modificado))
        db.commit()  # por archivo: si se corta, lo hecho queda
        hechos += 1
    for borrado in set(previos) - vistos:
        db.execute("DELETE FROM trozos WHERE archivo = ?", (borrado,))
        db.execute("DELETE FROM archivos WHERE ruta = ?", (borrado,))
    db.commit()
    db.close()
    return hechos


def buscar(raiz, pregunta, embeber, k=5):
    """Los k trozos de código más parecidos y, al final, el mejor trozo de documentación si lo hay.

    pregunta puede ser una lista con la misma pregunta en varios idiomas: cuenta la versión que más se parece.
    Los documentos van aparte porque, con preguntas en español, los .md en español tapaban al código en inglés.
    """
    # shortcut: compara contra todos los trozos en Python; va bien hasta ~10 000 trozos, después FAISS o sqlite-vec
    db = _abrir(str(raiz), crear=False)
    versiones = [pregunta] if isinstance(pregunta, str) else pregunta
    consultas = [_normal(v) for v in embeber([PREFIJO_PREGUNTA + p for p in versiones])]
    codigo, documentos = [], []
    for archivo, linea, texto, blob in db.execute("SELECT archivo, linea, texto, vector FROM trozos"):
        vector = array("f")
        vector.frombytes(blob)
        puntaje = max(sum(map(float.__mul__, c, vector)) for c in consultas)
        destino = documentos if archivo.lower().endswith(DOCUMENTOS) else codigo
        destino.append(Resultado(archivo, linea, texto, puntaje))
    db.close()

    def mejores(lista, n):
        return sorted(lista, key=lambda r: -r.puntaje)[:n]
    return mejores(codigo, k) + mejores(documentos, 1)


def _en_ingles(pregunta, modelo):
    """El código suele estar en inglés y el modelo de embeddings cruza mal de idioma: se busca en los dos."""
    try:
        traduccion = modelo("Translate this question about a codebase to English. "
                            f"Answer with the translation only.\n\n{pregunta}").strip()
    except OSError:
        return [pregunta]
    return [pregunta, traduccion] if traduccion and len(traduccion) < 4 * len(pregunta) + 40 else [pregunta]


def preguntar(raiz, pregunta, embeber, modelo, k=5):
    """Respuesta del modelo con las fuentes al final. El modelo solo ve lo que trajo la búsqueda."""
    hallados = buscar(raiz, _en_ingles(pregunta, modelo), embeber, k)
    fragmentos = "\n\n".join(f"### {r.archivo}:{r.linea}\n{tapar(r.texto[:3000])}" for r in hallados)
    respuesta = modelo(f"""Responde en español la pregunta sobre este repositorio usando solo los fragmentos de abajo.
Cita el archivo y la línea de donde sale cada afirmación. Si los fragmentos no alcanzan para responder, dilo.

Pregunta: {pregunta}

{fragmentos}
""").strip()
    return respuesta + "\n\nFuentes:\n" + "\n".join(f"- {r.archivo}:{r.linea}" for r in hallados) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(prog="repo", description="Pregunta sobre un repositorio con modelos locales.")
    sub = p.add_subparsers(dest="orden", required=True)
    i = sub.add_parser("indexar", help="crea o actualiza el índice en <ruta>/.agentes")
    q = sub.add_parser("preguntar")
    q.add_argument("pregunta")
    q.add_argument("-k", type=int, default=5, help="cuántos trozos usar")
    q.add_argument("--sin-ia", action="store_true", help="solo lista los trozos encontrados")
    q.add_argument("--modelo", default="qwen2.5-coder:7b")
    for s in (i, q):
        s.add_argument("--ruta", default=".")
    a = p.parse_args(argv)
    embeber = cliente_embeddings()
    try:
        if a.orden == "indexar":
            n = indexar(a.ruta, embeber, avisar=lambda r: print(r, flush=True))
            print(f"{n} archivos indexados")
        elif a.sin_ia:
            for r in buscar(a.ruta, a.pregunta, embeber, a.k):  # sin modelo no hay traducción al inglés
                print(f"{r.puntaje:.2f}  {r.archivo}:{r.linea}")
        else:
            print(preguntar(a.ruta, a.pregunta, embeber, cliente_ollama(a.modelo, contexto=8192), a.k), end="")
    except FileNotFoundError as e:
        sys.exit(str(e))
    except OSError as e:
        sys.exit(f"No pude hablar con Ollama ({e}). ¿Está abierto y con nomic-embed-text descargado?")


if __name__ == "__main__":
    main()
