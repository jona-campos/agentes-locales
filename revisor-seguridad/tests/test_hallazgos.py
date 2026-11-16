"""Normalización y agrupación de hallazgos, probadas con salidas reales de los escáneres.

Las salidas en tests/salidas/ se generaron sobre fixtures/vulnerable. Donde el escáner escribió la
ruta absoluta del fixture hay un marcador {RAIZ}; cargar() lo cambia por la ruta de este equipo.
"""
import json
import os
import unittest

from revisor import hallazgos as h

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDAS = os.path.join(AQUI, "salidas")
RAIZ = os.path.normpath(os.path.join(AQUI, "..", "fixtures", "vulnerable"))


def cargar(nombre):
    with open(os.path.join(SALIDAS, nombre), encoding="utf-8") as f:
        return json.loads(f.read().replace("{RAIZ}", json.dumps(RAIZ)[1:-1]))


def esperado():
    with open(os.path.join(RAIZ, "esperado.json"), encoding="utf-8") as f:
        return json.load(f)


def todo_el_codigo():
    return (h.desde_gitleaks(cargar("gitleaks.json"), RAIZ)
            + h.desde_bandit(cargar("bandit.json"), RAIZ)
            + h.desde_semgrep(cargar("semgrep.json"), RAIZ))


class Lectores(unittest.TestCase):
    def test_gitleaks(self):
        r = h.desde_gitleaks(cargar("gitleaks.json"), RAIZ)
        self.assertEqual({(x.archivo, x.linea_inicio) for x in r}, {("config.py", 6), ("config.py", 7)})
        self.assertTrue(all(x.herramienta == "gitleaks" and x.severidad == "alta" for x in r))

    def test_gitleaks_no_copia_el_secreto(self):
        r = h.desde_gitleaks(cargar("gitleaks.json"), RAIZ)
        self.assertNotIn("ghp_", repr(r))

    def test_bandit(self):
        r = h.desde_bandit(cargar("bandit.json"), RAIZ)
        self.assertEqual(len(r), 20)
        sqli = [x for x in r if x.regla == "B608"][0]
        self.assertEqual((sqli.archivo, sqli.linea_inicio, sqli.severidad), ("app.py", 20, "media"))

    def test_semgrep_usa_rango_y_nombre_corto(self):
        r = h.desde_semgrep(cargar("semgrep.json"), RAIZ)
        self.assertEqual(len(r), 31)
        x = [x for x in r if x.regla == "sql-injection-db-cursor-execute"][0]
        self.assertEqual((x.archivo, x.linea_inicio, x.linea_fin), ("app.py", 19, 20))
        self.assertTrue(all(x.linea_inicio <= x.linea_fin for x in r))
        self.assertIn("static/app.js", {x.archivo for x in r})

    def test_osv_un_hallazgo_por_vulnerabilidad_sin_duplicar_alias(self):
        r = h.desde_osv(cargar("osv.json"), RAIZ)
        flask = [x for x in r if x.paquete == "flask@0.12.2"]
        self.assertEqual(len(flask), 4)  # osv lista 8 entradas, pero son 4 fallos con sus alias (CVE/GHSA/PYSEC)
        self.assertTrue(all(x.archivo == "requirements.txt" and x.linea_inicio == 0 for x in flask))
        self.assertIn("alta", {x.severidad for x in flask})


class Agrupacion(unittest.TestCase):
    def test_cada_fallo_esperado_cae_en_un_solo_grupo(self):
        grupos = h.agrupar(todo_el_codigo())
        for e in esperado():
            if e["tipo"] == "dependencia" or e["id"] == "FP-INNERHTML-CONSTANTE":
                continue  # dependencias van aparte; ese falso positivo ningún escáner lo marca
            with self.subTest(e["id"]):
                dentro = [g for g in grupos if g.archivo == e["archivo"] and g.linea_inicio <= e["linea"] <= g.linea_fin]
                self.assertEqual(len(dentro), 1)

    def test_lineas_vecinas_no_se_mezclan(self):
        grupos = h.agrupar(todo_el_codigo())
        config = sorted(g.linea_inicio for g in grupos if g.archivo == "config.py")
        self.assertEqual(config, [4, 5, 6, 7])
        self.assertEqual(len([g for g in grupos if g.archivo == "app.py" and g.linea_inicio <= 66 and g.linea_fin >= 65]), 2)

    def test_reune_herramientas_y_toma_la_peor_severidad(self):
        grupos = h.agrupar(todo_el_codigo())
        sqli = [g for g in grupos if g.archivo == "app.py" and g.linea_inicio <= 20 <= g.linea_fin][0]
        self.assertEqual({x.herramienta for x in sqli.hallazgos}, {"bandit", "semgrep"})
        self.assertEqual(sqli.severidad, max((x.severidad for x in sqli.hallazgos), key=h.ORDEN_SEVERIDAD.index))

    def test_muchos_menos_grupos_que_hallazgos(self):
        codigo = todo_el_codigo()
        self.assertEqual(len(codigo), 53)
        self.assertLessEqual(len(h.agrupar(codigo)), 22)

    def test_dependencias_un_grupo_por_paquete(self):
        grupos = h.agrupar(h.desde_osv(cargar("osv.json"), RAIZ))
        paquetes = {g.hallazgos[0].paquete.split("@")[0] for g in grupos}
        self.assertEqual(len(grupos), len(paquetes))
        self.assertTrue({"flask", "pyyaml", "requests"} <= paquetes)


if __name__ == "__main__":
    unittest.main()
