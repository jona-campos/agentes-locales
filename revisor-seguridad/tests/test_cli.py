"""Comando `revisor escanear` de punta a punta con los escáneres reales (tarda ~1 min).

Se escanea una copia del fixture en una carpeta temporal para no dejar .revisor/ dentro del fixture.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from revisor import escaneo, informe
from tests.test_hallazgos import RAIZ

PROYECTO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SECRETOS = ("ghp_7Kq2", "AKIAZ3MQ", "q8Jx2Lm9", "Tienda2026")


def revisor(*args):
    return subprocess.run([sys.executable, "-m", "revisor", *args], cwd=PROYECTO, capture_output=True,
                          text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.copia = os.path.join(cls.tmp, "tienda")
        shutil.copytree(RAIZ, cls.copia)
        cls.r = revisor("escanear", cls.copia, "--sin-ia")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_termina_bien_y_deja_informe(self):
        self.assertEqual(self.r.returncode, 0, self.r.stderr[-2000:])
        self.assertEqual(len(glob.glob(os.path.join(self.copia, ".revisor", "informe-*.md"))), 1)

    def test_el_json_tiene_todo_sin_revisar_y_las_dependencias(self):
        with open(glob.glob(os.path.join(self.copia, ".revisor", "informe-*.json"))[0], encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["proyecto"], "tienda")
        self.assertIsNone(d["modelo"])
        self.assertGreaterEqual(d["resumen"]["sin_revisar"], 17)
        self.assertEqual(d["resumen"]["real"], 0)
        self.assertGreaterEqual(d["resumen"]["dependencias"], 3)
        self.assertEqual(d["avisos"], [])

    def test_no_hay_secretos_ni_en_el_informe_ni_en_la_terminal(self):
        textos = [self.r.stdout, self.r.stderr]
        for ruta in glob.glob(os.path.join(self.copia, ".revisor", "*")):
            with open(ruta, encoding="utf-8") as f:
                textos.append(f.read())
        for s in SECRETOS:
            self.assertNotIn(s, "".join(textos))

    def test_dice_donde_quedo_el_informe(self):
        self.assertIn(".revisor", self.r.stdout)


class Errores(unittest.TestCase):
    def test_ruta_inexistente(self):
        r = revisor("escanear", os.path.join(PROYECTO, "no-existe"), "--sin-ia")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no existe", r.stderr)

    def test_un_escaner_que_falla_no_frena_a_los_demas(self):
        with tempfile.TemporaryDirectory() as tmp:
            hallazgos, avisos = escaneo.ejecutar(RAIZ, tmp, rutas={"gitleaks": os.path.join(tmp, "no-esta.exe")})
        self.assertTrue(any("gitleaks" in a for a in avisos), avisos)
        self.assertEqual({x.herramienta for x in hallazgos}, {"bandit", "semgrep", "osv-scanner"})

    def test_los_avisos_salen_en_el_informe(self):
        md, d = informe.generar("x", [], "2026-11-07T22:00:00", None, avisos=["gitleaks: no se encontró"])
        self.assertIn("gitleaks: no se encontró", md)
        self.assertEqual(d["avisos"], ["gitleaks: no se encontró"])


if __name__ == "__main__":
    unittest.main()
