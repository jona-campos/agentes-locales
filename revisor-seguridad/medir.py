"""Mide escáneres y triaje contra el esperado.json de un fixture, escaneando en vivo.

Uso: .venv/Scripts/python.exe medir.py fixtures/vulnerable2 [modelo | --sin-ia]
"""
import json
import os
import sys
import tempfile
import time

from revisor import escaneo, triaje
from revisor.hallazgos import agrupar

raiz = os.path.abspath(sys.argv[1])
modelo = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5-coder:7b"
with open(os.path.join(raiz, "esperado.json"), encoding="utf-8") as f:
    esp = json.load(f)

inicio = time.time()
with tempfile.TemporaryDirectory() as tmp:
    hallazgos, avisos = escaneo.ejecutar(raiz, tmp)
grupos = agrupar(hallazgos)
t_escaneo = time.time() - inicio
paquetes = {g.hallazgos[0].paquete.split("@")[0] for g in grupos if g.hallazgos[0].paquete}
codigo = [g for g in grupos if not g.hallazgos[0].paquete]


def grupo_de(e):
    return next((g for g in codigo if g.archivo == e["archivo"] and g.linea_inicio <= e["linea"] <= g.linea_fin), None)


print(f"== Escáneres ({t_escaneo:.0f} s) {avisos or ''}")
for e in esp:
    visto = e["contiene"].split("==")[0] in paquetes if e["tipo"] == "dependencia" else grupo_de(e) is not None
    print(f"  {'REAL' if e['real'] else 'FP  '} {'detectado' if visto else 'NO DETECTADO':12} {e['id']}")

if modelo == "--sin-ia":
    sys.exit()
consultar, filas = triaje.cliente_ollama(modelo), []
print(f"\n== Triaje con {modelo}")
for g in codigo:
    s = time.time()
    r = triaje.triar(g, raiz, consultar)
    e = [x for x in esp if x["archivo"] == g.archivo and g.linea_inicio <= x["linea"] <= g.linea_fin]
    verdad = ("real" if e[0]["real"] else "falso_positivo") if e else "ruido"
    ok = r.veredicto == verdad or (verdad == "ruido" and r.veredicto != "real")
    filas.append((verdad, r.veredicto))
    print(f"  {'OK ' if ok else 'MAL'} {g.archivo}:{g.linea_inicio:<3} verdad={verdad:14} modelo={r.veredicto:14} {time.time() - s:5.1f}s",
          flush=True)
n = lambda v, m=None: sum(1 for a, b in filas if a == v and (m is None or b == m))
print(f"\nRESUMEN {os.path.basename(raiz)} {modelo}: reales confirmados {n('real', 'real')}/{n('real')} | "
      f"falsos positivos descartados {n('falso_positivo', 'falso_positivo')}/{n('falso_positivo')} | "
      f"ruido no marcado real {n('ruido') - n('ruido', 'real')}/{n('ruido')} | "
      f"sin revisar {sum(b == 'sin_revisar' for _, b in filas)} | escaneo {t_escaneo:.0f}s | total {time.time() - inicio:.0f}s")
