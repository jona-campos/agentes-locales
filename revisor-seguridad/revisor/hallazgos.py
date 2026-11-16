"""Convierte las salidas JSON de cada escáner a una lista común y la agrupa por ubicación."""
import os
import re
from dataclasses import dataclass, field

ORDEN_SEVERIDAD = ["baja", "media", "alta"]


@dataclass(frozen=True)
class Hallazgo:
    herramienta: str
    regla: str
    archivo: str  # relativo a la raíz del proyecto, con "/"
    linea_inicio: int  # 0 = el archivo entero (dependencias)
    linea_fin: int
    severidad: str  # baja | media | alta
    mensaje: str
    paquete: str = ""  # "nombre@versión", solo dependencias


@dataclass
class Grupo:
    archivo: str
    linea_inicio: int
    linea_fin: int
    hallazgos: list = field(default_factory=list)

    @property
    def severidad(self):
        return max((x.severidad for x in self.hallazgos), key=ORDEN_SEVERIDAD.index)


_LITERAL = re.compile(r"([\"'])([^\"']*)\1")


def _sin_secretos(texto, todo=False):
    """Tapa los literales con pinta de secreto (10+ caracteres sin espacios, con letras y números); con todo=True, todos."""
    def tapar(m):
        s = m.group(2)
        parece = len(s) >= 10 and " " not in s and re.search(r"\d", s) and re.search(r"[A-Za-z]", s)
        return f"{m.group(1)}[oculto]{m.group(1)}" if todo or parece else m.group(0)
    return _LITERAL.sub(tapar, texto)


def _relativa(ruta, raiz):
    return os.path.relpath(os.path.normpath(ruta), os.path.normpath(raiz)).replace("\\", "/")


def desde_gitleaks(datos, raiz):
    # no se copian "Secret" ni "Match": el informe nunca debe repetir el secreto
    return [Hallazgo("gitleaks", g["RuleID"], _relativa(g["File"], raiz), g["StartLine"], g["EndLine"],
                     "alta", g["Description"]) for g in datos or []]


def desde_bandit(datos, raiz):
    sev = {"HIGH": "alta", "MEDIUM": "media", "LOW": "baja"}
    return [Hallazgo("bandit", b["test_id"], _relativa(b["filename"], raiz),
                     min(b["line_range"] or [b["line_number"]]), max(b["line_range"] or [b["line_number"]]),
                     sev.get(b["issue_severity"], "media"),
                     # B105-B107 ("hardcoded password") copian el valor de la contraseña en el mensaje
                     _sin_secretos(b["issue_text"], todo=b["test_id"] in ("B105", "B106", "B107")))
            for b in datos.get("results", [])]


def desde_semgrep(datos, raiz):
    sev = {"ERROR": "alta", "WARNING": "media", "INFO": "baja"}
    return [Hallazgo("semgrep", s["check_id"].split(".")[-1], _relativa(s["path"], raiz),
                     s["start"]["line"], s["end"]["line"], sev.get(s["extra"]["severity"], "media"),
                     _sin_secretos(s["extra"]["message"].strip())) for s in datos.get("results", [])]


def _severidad_cvss(texto):
    try:
        nota = float(texto)
    except (TypeError, ValueError):
        return "media"  # sin puntuación: ni se esconde ni se exagera
    return "alta" if nota >= 7 else "media" if nota >= 4 else "baja"


def desde_osv(datos, raiz):
    resultado = []
    for r in datos.get("results", []):
        archivo = _relativa(r["source"]["path"], raiz)
        for p in r["packages"]:
            paquete = f'{p["package"]["name"].lower()}@{p["package"]["version"]}'
            for g in p.get("groups", []):  # un grupo = una vulnerabilidad con todos sus alias
                resultado.append(Hallazgo("osv-scanner", g["ids"][0], archivo, 0, 0,
                                          _severidad_cvss(g.get("max_severity")),
                                          ", ".join(sorted(set(g.get("aliases") or g["ids"]))), paquete))
    return resultado


def agrupar(hallazgos):
    """Une los hallazgos del mismo archivo cuyos rangos de líneas se solapan; las dependencias, por paquete."""
    grupos = {}
    codigo = []
    for x in hallazgos:
        if x.paquete:
            grupos.setdefault((x.archivo, x.paquete), Grupo(x.archivo, 0, 0)).hallazgos.append(x)
        else:
            codigo.append(x)
    resultado = list(grupos.values())
    actual = None
    for x in sorted(codigo, key=lambda x: (x.archivo, x.linea_inicio, x.linea_fin)):
        if actual and x.archivo == actual.archivo and x.linea_inicio <= actual.linea_fin:
            actual.linea_fin = max(actual.linea_fin, x.linea_fin)
            actual.hallazgos.append(x)
        else:
            actual = Grupo(x.archivo, x.linea_inicio, x.linea_fin, [x])
            resultado.append(actual)
    return resultado
