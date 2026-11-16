"""Informe en Markdown (para leer) y JSON (para la app futura)."""
import json
import os
import tempfile
import unittest

from revisor import hallazgos as h
from revisor import informe as inf
from revisor.triaje import Triaje
from tests.test_hallazgos import RAIZ, cargar


def H(archivo, linea, regla="R1", sev="alta", paquete="", herramienta="semgrep"):
    return h.Hallazgo(herramienta, regla, archivo, linea, linea, sev, f"mensaje de {regla}", paquete)


def G(*hs):
    return h.Grupo(hs[0].archivo, hs[0].linea_inicio, hs[0].linea_fin, list(hs))


def T(veredicto, sev="alta", revisado=True):
    return Triaje(veredicto, sev, f"explicación {veredicto}", "arreglo X" if veredicto == "real" else "", revisado)


def ejemplo():
    return [
        (G(H("a.py", 5, "FP1")), T("falso_positivo", "baja")),
        (G(H("a.py", 9, "MEDIA")), T("real", "media")),
        (G(H("b.py", 2, "ALTA")), T("real", "alta")),
        (G(H("c.py", 7, "DUDA")), T("dudoso", "media")),
        (G(H("d.py", 1, "ROTO")), T("sin_revisar", "alta", revisado=False)),
        (G(H("requirements.txt", 0, "PYSEC-1", "alta", "flask@0.12.2", "osv-scanner"),
           H("requirements.txt", 0, "PYSEC-2", "media", "flask@0.12.2", "osv-scanner")), None),
    ]


class Informe(unittest.TestCase):
    def setUp(self):
        self.md, self.datos = inf.generar("tienda", ejemplo(), "2026-11-07T22:00:00", "qwen2.5-coder:7b")

    def test_orden_reales_por_severidad_luego_dudosos_sin_revisar_y_al_final_falsos(self):
        pos = [self.md.index(x) for x in ("b.py:2", "a.py:9", "c.py:7", "d.py:1", "a.py:5")]
        self.assertEqual(pos, sorted(pos))
        self.assertLess(self.md.index("<details>"), self.md.index("a.py:5"))

    def test_resumen(self):
        r = self.datos["resumen"]
        self.assertEqual((r["real"], r["dudoso"], r["sin_revisar"], r["falso_positivo"], r["dependencias"]), (2, 1, 1, 1, 1))
        self.assertIn("| Reales | 2 |", self.md)

    def test_dependencias_con_sus_ids(self):
        self.assertIn("flask@0.12.2", self.md)
        self.assertIn("PYSEC-1", self.md)
        self.assertEqual(self.datos["dependencias"][0]["severidad"], "alta")

    def test_sin_revisar_avisa(self):
        self.assertIn("sin revisar", self.md.lower())

    def test_json_completo_y_serializable(self):
        d = json.loads(json.dumps(self.datos))
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["modelo"], "qwen2.5-coder:7b")
        self.assertEqual(len(d["problemas"]), 5)
        p = [x for x in d["problemas"] if x["archivo"] == "b.py"][0]
        self.assertEqual((p["veredicto"], p["arreglo"], p["hallazgos"][0]["regla"]), ("real", "arreglo X", "ALTA"))

    def test_guardar_en_carpeta_revisor(self):
        with tempfile.TemporaryDirectory() as d:
            md_ruta, json_ruta = inf.guardar(d, self.md, self.datos, "20261107-220000")
            self.assertEqual(os.path.dirname(md_ruta), os.path.join(d, ".revisor"))
            self.assertTrue(md_ruta.endswith("informe-20261107-220000.md"))
            with open(json_ruta, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["proyecto"], "tienda")

    def test_sin_modelo(self):
        md, datos = inf.generar("tienda", [(g, None) for g, _ in ejemplo()], "2026-11-07T22:00:00", None)
        self.assertIn("sin IA", md)
        self.assertEqual(datos["resumen"]["sin_revisar"], 5)

    def test_no_incluye_secretos_del_fixture(self):
        # bandit B105 mete el valor de la contraseña en su mensaje: pasó en el primer informe real
        codigo = (h.desde_gitleaks(cargar("gitleaks.json"), RAIZ) + h.desde_semgrep(cargar("semgrep.json"), RAIZ)
                  + h.desde_bandit(cargar("bandit.json"), RAIZ))
        md, datos = inf.generar("fixture", [(g, None) for g in h.agrupar(codigo)], "2026-11-07T22:00:00", None)
        for secreto in ("ghp_7Kq2", "AKIAZ3MQ", "q8Jx2Lm9", "Tienda2026"):
            self.assertNotIn(secreto, md + json.dumps(datos))


if __name__ == "__main__":
    unittest.main()
