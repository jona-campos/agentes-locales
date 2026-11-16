"""revisor escanear <ruta> [--sin-ia] [--modelo X]"""
import argparse
import os
import sys
import tempfile
import time

from revisor import actualizar, escaneo, informe, triaje
from revisor.hallazgos import ORDEN_SEVERIDAD, agrupar


def elegir_para_ia(grupos, tope):
    """Los `tope` grupos de mayor severidad (los demás quedan sin revisar); a igual severidad, el orden original."""
    return sorted(grupos, key=lambda g: -ORDEN_SEVERIDAD.index(g.severidad))[:max(tope, 0)]


def escanear(ruta, sin_ia, modelo, max_ia=150):
    if not os.path.isdir(ruta):
        print(f"revisor: la carpeta {ruta} no existe", file=sys.stderr)
        return 2
    inicio = time.time()
    print(f"Escaneando {ruta} ...", file=sys.stderr, flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        hallazgos, avisos = escaneo.ejecutar(ruta, tmp)
    grupos = agrupar(hallazgos)
    consultar = None
    if not sin_ia:
        if triaje.ollama_disponible():
            consultar = triaje.cliente_ollama(modelo)
        else:
            avisos.append("Ollama no responde en localhost:11434: el informe se hizo sin IA")
    codigo = [g for g in grupos if not g.hallazgos[0].paquete]
    elegidos = {id(g) for g in elegir_para_ia(codigo, max_ia)} if consultar else set()
    if consultar and len(elegidos) < len(codigo):
        avisos.append(f"La IA revisó {len(elegidos)} de {len(codigo)} grupos (--max-ia {max_ia}): "
                      "los de mayor severidad primero; el resto quedó sin revisar")
    pares = []
    for g in grupos:
        t = None
        if id(g) in elegidos:
            t = triaje.triar(g, ruta, consultar)
            print(f"[{len(pares) + 1}/{len(codigo)}] {g.archivo}:{g.linea_inicio} -> {t.veredicto}",
                  file=sys.stderr, flush=True)
        if not g.hallazgos[0].paquete:
            pares.append((g, t))
    pares += [(g, None) for g in grupos if g.hallazgos[0].paquete]
    md, datos = informe.generar(os.path.basename(ruta), pares, time.strftime("%Y-%m-%dT%H:%M:%S"),
                                modelo if consultar else None, avisos)
    ruta_md, _ = informe.guardar(ruta, md, datos, time.strftime("%Y%m%d-%H%M%S"))
    r = datos["resumen"]
    print(f"Reales {r['real']} · dudosos {r['dudoso']} · sin revisar {r['sin_revisar']} · "
          f"falsos positivos {r['falso_positivo']} · paquetes vulnerables {r['dependencias']} "
          f"({time.time() - inicio:.0f} s)")
    for a in avisos:
        print(f"Aviso: {a}")
    print(f"Informe: {ruta_md}")
    return 0


def parser():
    p = argparse.ArgumentParser(prog="revisor", description="Revisor de seguridad local")
    sub = p.add_subparsers(dest="orden", required=True)
    e = sub.add_parser("escanear", help="revisa un proyecto y deja el informe en <ruta>/.revisor/")
    e.add_argument("ruta")
    e.add_argument("--sin-ia", action="store_true", help="solo escáneres, sin modelo")
    e.add_argument("--modelo", default="qwen2.5-coder:7b")
    sub.add_parser("actualizar", help="descarga reglas de Semgrep y bases de osv-scanner (usa internet)")
    e.add_argument("--max-ia", type=int, default=150, help="máximo de grupos que revisa el modelo")
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    if a.orden == "actualizar":
        avisos = actualizar.actualizar()
        for x in avisos:
            print(f"Aviso: {x}")
        print("Actualizado" if not avisos else "Actualizado con avisos")
        return 1 if avisos else 0
    return escanear(os.path.abspath(a.ruta), a.sin_ia, a.modelo, a.max_ia)
