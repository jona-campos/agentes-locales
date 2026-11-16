"""Cada proyecto de prueba en fixtures/ y su lista de fallos esperados deben coincidir.

esperado.json es la "verdad" contra la que se mide el revisor: si alguien mueve una
línea de un fixture, esta prueba avisa antes de que las mediciones salgan mal.
"""
import json
import os
import unittest

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures")
RAICES = sorted(os.path.join(FIXTURES, d) for d in os.listdir(FIXTURES)
                if os.path.isfile(os.path.join(FIXTURES, d, "esperado.json")))


def esperado(raiz):
    with open(os.path.join(raiz, "esperado.json"), encoding="utf-8") as f:
        return json.load(f)


class Fixture(unittest.TestCase):
    def test_hay_al_menos_dos_fixtures(self):
        self.assertGreaterEqual(len(RAICES), 2)

    def test_cada_fallo_apunta_a_su_linea(self):
        for raiz in RAICES:
            for f in esperado(raiz):
                with self.subTest(fixture=os.path.basename(raiz), id=f["id"]):
                    with open(os.path.join(raiz, f["archivo"]), encoding="utf-8") as a:
                        lineas = a.read().splitlines()
                    self.assertIn(f["contiene"], lineas[f["linea"] - 1])

    def test_ids_unicos_y_hay_reales_y_falsos(self):
        for raiz in RAICES:
            with self.subTest(os.path.basename(raiz)):
                fallos = esperado(raiz)
                self.assertEqual(len({f["id"] for f in fallos}), len(fallos))
                self.assertGreaterEqual(sum(f["real"] for f in fallos), 10)
                self.assertGreaterEqual(sum(not f["real"] for f in fallos), 3)

    def test_el_codigo_no_delata_los_fallos(self):
        # el modelo verá el código: ningún comentario debe decirle qué es vulnerable
        for raiz in RAICES:
            for carpeta, _, archivos in os.walk(raiz):
                for nombre in archivos:
                    if nombre == "esperado.json":
                        continue
                    with open(os.path.join(carpeta, nombre), encoding="utf-8") as a:
                        texto = a.read().lower()
                    for palabra in ("vulnerab", "plantad", "inseguro", "falso positivo", "inyecci"):
                        self.assertNotIn(palabra, texto, f"{nombre} contiene '{palabra}'")


if __name__ == "__main__":
    unittest.main()
