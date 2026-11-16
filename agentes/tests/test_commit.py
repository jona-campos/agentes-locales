import json
import unittest

from agentes import commit


def diff_de(archivo, lineas):
    return f"diff --git a/{archivo} b/{archivo}\n--- a/{archivo}\n+++ b/{archivo}\n@@ -1 +1,{lineas} @@\n" + \
        "".join(f"+linea {i}\n" for i in range(lineas))


class TestRecortar(unittest.TestCase):
    def test_diff_corto_no_cambia(self):
        d = diff_de("a.py", 5)
        self.assertEqual(commit.recortar_diff(d), d)

    def test_archivo_largo_se_corta_y_avisa(self):
        r = commit.recortar_diff(diff_de("a.py", 300) + diff_de("b.py", 3), por_archivo=50)
        self.assertIn("+linea 10\n", r)
        self.assertNotIn("+linea 200\n", r)
        self.assertIn("líneas omitidas", r)
        self.assertIn("b/b.py", r)  # el segundo archivo sigue entero

    def test_tope_total(self):
        r = commit.recortar_diff("".join(diff_de(f"f{i}.py", 40) for i in range(30)), por_archivo=50, total=200)
        self.assertLessEqual(len(r.splitlines()), 201)


class TestInterpretar(unittest.TestCase):
    def test_mensaje_valido(self):
        m = commit.interpretar(json.dumps({"tipo": "fix", "ambito": "caja", "resumen": "corrige el redondeo del IVA"}))
        self.assertEqual(m, "fix(caja): corrige el redondeo del IVA")

    def test_sin_ambito_y_con_cuerpo(self):
        m = commit.interpretar(json.dumps({"tipo": "feat", "ambito": "", "resumen": "Agrega el cierre de caja.",
                                           "cuerpo": "Suma ventas y devoluciones."}))
        self.assertEqual(m, "feat: Agrega el cierre de caja\n\nSuma ventas y devoluciones.")

    def test_tipo_inventado_o_titulo_largo_no_valen(self):
        for malo in ({"tipo": "mejora", "resumen": "x"}, {"tipo": "fix", "resumen": "x" * 80},
                     {"tipo": "fix", "resumen": ""}):
            with self.assertRaises(ValueError):
                commit.interpretar(json.dumps(malo))
        with self.assertRaises(ValueError):
            commit.interpretar("no es json")


class TestSugerir(unittest.TestCase):
    def test_reintenta_una_vez_y_tapa_secretos(self):
        vistos = []

        def modelo(texto):
            vistos.append(texto)
            return "basura" if len(vistos) == 1 else json.dumps({"tipo": "chore", "resumen": "actualiza la clave"})
        clave = "abc" + "123def456ghi789"
        m = commit.sugerir(f'diff --git a/x b/x\n+K = "{clave}"\n', " x | 1 +", modelo)
        self.assertEqual(m, "chore: actualiza la clave")
        self.assertEqual(len(vistos), 2)
        self.assertNotIn(clave, vistos[0])

    def test_el_reintento_le_dice_al_modelo_que_estuvo_mal(self):
        vistos = []

        def modelo(texto):
            vistos.append(texto)
            largo = "x" * 90 if len(vistos) == 1 else "acorta el título"
            return json.dumps({"tipo": "fix", "resumen": largo})
        self.assertEqual(commit.sugerir("diff --git a/x b/x\n+1\n", "", modelo), "fix: acorta el título")
        self.assertIn("título de 95 caracteres", vistos[1])

    def test_el_tipo_lo_fija_el_codigo_si_solo_cambian_documentos_o_pruebas(self):
        def modelo(texto):
            return json.dumps({"tipo": "fix", "ambito": "plan", "resumen": "registra la fase 7"})
        self.assertEqual(commit.sugerir(diff_de("docs/plan.md", 2) + diff_de("README.md", 1), "", modelo),
                         "docs(plan): registra la fase 7")
        self.assertEqual(commit.sugerir(diff_de("app/test/caja_test.dart", 2), "", modelo),
                         "test(plan): registra la fase 7")
        self.assertEqual(commit.sugerir(diff_de("docs/plan.md", 2) + diff_de("caja.py", 1), "", modelo),
                         "fix(plan): registra la fase 7")

    def test_si_el_modelo_falla_dos_veces_devuelve_none(self):
        self.assertIsNone(commit.sugerir("diff --git a/x b/x\n+1\n", "", lambda t: "nada"))


class TestChangelog(unittest.TestCase):
    def test_agrupa_por_tipo_y_deja_el_resto_en_otros(self):
        md = commit.changelog(["feat(caja): cierre diario", "fix: redondeo del IVA", "feat!: nueva API",
                               "Merge pull request #1", "arreglos varios"])
        self.assertLess(md.index("## Novedades"), md.index("## Correcciones"))
        self.assertIn("- **caja:** cierre diario", md)
        self.assertIn("- nueva API (cambio incompatible)", md)
        self.assertIn("## Otros\n\n- arreglos varios", md)
        self.assertNotIn("Merge pull request", md)


if __name__ == "__main__":
    unittest.main()
