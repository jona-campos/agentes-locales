"""Arma el informe: Markdown para leer y JSON para la app. No incluye código fuente, para no repetir secretos."""
import json
import os

from revisor.hallazgos import ORDEN_SEVERIDAD
from revisor.triaje import Triaje

ORDEN_VEREDICTO = ["real", "dudoso", "sin_revisar", "falso_positivo"]
TITULOS = {"real": "Reales", "dudoso": "Dudosos", "sin_revisar": "Sin revisar",
           "falso_positivo": "Falsos positivos (según el modelo)"}


def _donde(p):
    lineas = p["linea_inicio"] if p["linea_inicio"] == p["linea_fin"] else f'{p["linea_inicio"]}-{p["linea_fin"]}'
    return f'{p["archivo"]}:{lineas}'


def _corto(texto, n=200):
    texto = " ".join(texto.split())
    return texto if len(texto) <= n else texto[:n - 1] + "…"


def generar(proyecto, pares, fecha, modelo, avisos=None):
    """pares: lista de (Grupo, Triaje o None). Las dependencias se reconocen por su paquete."""
    problemas, dependencias = [], []
    for g, t in pares:
        hallazgos = [{"herramienta": x.herramienta, "regla": x.regla, "mensaje": _corto(x.mensaje)} for x in g.hallazgos]
        if g.hallazgos[0].paquete:
            dependencias.append({"paquete": g.hallazgos[0].paquete, "archivo": g.archivo, "severidad": g.severidad,
                                 "vulnerabilidades": [{"id": x.regla, "alias": x.mensaje} for x in g.hallazgos]})
            continue
        t = t or Triaje("sin_revisar", g.severidad, "No se usó el modelo (revisión sin IA).", "", False)
        problemas.append({"archivo": g.archivo, "linea_inicio": g.linea_inicio, "linea_fin": g.linea_fin,
                          "severidad_escaner": g.severidad, "veredicto": t.veredicto, "severidad": t.severidad,
                          "explicacion": t.explicacion, "arreglo": t.arreglo, "revisado": t.revisado,
                          "hallazgos": hallazgos})
    problemas.sort(key=lambda p: (ORDEN_VEREDICTO.index(p["veredicto"]), -ORDEN_SEVERIDAD.index(p["severidad"]),
                                  p["archivo"], p["linea_inicio"]))
    dependencias.sort(key=lambda d: (-ORDEN_SEVERIDAD.index(d["severidad"]), d["paquete"]))
    resumen = {v: sum(p["veredicto"] == v for p in problemas) for v in ORDEN_VEREDICTO}
    resumen["dependencias"] = len(dependencias)
    datos = {"version": 1, "proyecto": proyecto, "fecha": fecha, "modelo": modelo, "resumen": resumen,
             "avisos": list(avisos or []), "problemas": problemas, "dependencias": dependencias}
    return _markdown(datos), datos


def _markdown(d):
    r = d["resumen"]
    md = [f'# Informe de seguridad: {d["proyecto"]}', "",
          f'Fecha: {d["fecha"]} · Modelo: {d["modelo"] or "ninguno (revisión sin IA)"}', "",
          "| Resultado | Cantidad |", "|---|---|",
          f'| Reales | {r["real"]} |', f'| Dudosos | {r["dudoso"]} |', f'| Sin revisar | {r["sin_revisar"]} |',
          f'| Falsos positivos (según el modelo) | {r["falso_positivo"]} |',
          f'| Paquetes con vulnerabilidades | {r["dependencias"]} |', "",
          "> El veredicto del modelo es una sugerencia: revisa siempre el hallazgo original.", ""]
    if d["avisos"]:
        md += ["## Avisos", "", "La revisión puede estar incompleta:", ""] + [f"- {a}" for a in d["avisos"]] + [""]
    for v in ORDEN_VEREDICTO:
        grupo = [p for p in d["problemas"] if p["veredicto"] == v]
        if v == "falso_positivo" and grupo:
            md += [f"## {TITULOS[v]}", "", f"<details><summary>Ver {len(grupo)}</summary>", ""]
        elif grupo:
            md += [f"## {TITULOS[v]}", ""]
            if v == "sin_revisar":
                md += ["El modelo no pudo revisarlos o no se usó: revísalos a mano.", ""]
        for p in grupo:
            md += [f'### [{p["severidad"].upper()}] {_donde(p)}', "", f'**Explicación:** {p["explicacion"]}', ""]
            if p["arreglo"]:
                md += [f'**Arreglo:** {p["arreglo"]}', ""]
            md += [f'- `{x["herramienta"]} {x["regla"]}`: {x["mensaje"]}' for x in p["hallazgos"]] + [""]
        if v == "falso_positivo" and grupo:
            md += ["</details>", ""]
    if d["dependencias"]:
        md += ["## Dependencias con vulnerabilidades conocidas", "",
               "| Paquete | Archivo | Severidad | Vulnerabilidades |", "|---|---|---|---|"]
        md += [f'| {x["paquete"]} | {x["archivo"]} | {x["severidad"]} | {", ".join(v["id"] for v in x["vulnerabilidades"])} |'
               for x in d["dependencias"]] + [""]
    return "\n".join(md)


def guardar(raiz, md, datos, marca):
    """Escribe <raiz>/.revisor/informe-<marca>.md y .json; devuelve sus rutas."""
    carpeta = os.path.join(raiz, ".revisor")
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.join(carpeta, f"informe-{marca}")
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return base + ".md", base + ".json"
