import os
import pathlib
import tempfile
import unittest

from agentes import repo

PALABRAS = ["factura", "inventario", "login"]


def embeber_falso(textos):
    """Un eje por palabra clave: el vector dice de qué habla el texto."""
    return [[float(t.lower().count(p)) + 0.01 for p in PALABRAS] for t in textos]


class TestTrocear(unittest.TestCase):
    def test_trozos_con_solape_y_numero_de_linea(self):
        texto = "".join(f"linea {i}\n" for i in range(1, 131))
        trozos = repo.trocear(texto, lineas=60, solape=10)
        self.assertEqual([t[0] for t in trozos], [1, 51, 101])
        self.assertTrue(trozos[1][1].startswith("linea 51\n"))
        self.assertTrue(trozos[-1][1].endswith("linea 130\n"))

    def test_archivo_corto_un_trozo_y_vacio_ninguno(self):
        self.assertEqual(repo.trocear("a\nb\n"), [(1, "a\nb\n")])
        self.assertEqual(repo.trocear("  \n"), [])


class TestIndice(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = pathlib.Path(self.tmp.name)
        (self.raiz / "src").mkdir()
        (self.raiz / "node_modules" / "x").mkdir(parents=True)
        (self.raiz / "src" / "facturas.py").write_text("def emitir():\n    # crea la factura y la factura firmada\n    pass\n")
        (self.raiz / "src" / "stock.dart").write_text("// inventario de bodega\nvoid contar() {}\n")
        (self.raiz / "node_modules" / "x" / "index.js").write_text("// factura factura factura\n")
        (self.raiz / "logo.png").write_bytes(b"\x89PNG\x00\x00")
        (self.raiz / ".env").write_text("CLAVE=factura\n")

    def test_indexa_solo_codigo_y_salta_generados_binarios_y_env(self):
        n = repo.indexar(self.raiz, embeber_falso)
        self.assertEqual(n, 2)
        self.assertTrue((self.raiz / ".agentes" / ".gitignore").exists())

    def test_buscar_devuelve_el_archivo_que_habla_del_tema(self):
        repo.indexar(self.raiz, embeber_falso)
        primero = repo.buscar(self.raiz, "¿dónde se cuenta el inventario?", embeber_falso, k=1)[0]
        self.assertEqual((primero.archivo, primero.linea), ("src/stock.dart", 1))
        self.assertEqual(repo.buscar(self.raiz, "factura", embeber_falso, k=1)[0].archivo, "src/facturas.py")

    def test_reindexar_solo_toca_lo_que_cambio_y_quita_lo_borrado(self):
        repo.indexar(self.raiz, embeber_falso)
        llamadas = []
        self.assertEqual(repo.indexar(self.raiz, lambda t: llamadas.append(t) or embeber_falso(t)), 0)
        self.assertEqual(llamadas, [])
        (self.raiz / "src" / "stock.dart").unlink()
        nuevo = self.raiz / "src" / "acceso.py"
        nuevo.write_text("def login():\n    pass\n")
        self.assertEqual(repo.indexar(self.raiz, embeber_falso), 1)
        archivos = {r.archivo for r in repo.buscar(self.raiz, "login", embeber_falso, k=10)}
        self.assertEqual(archivos, {"src/facturas.py", "src/acceso.py"})

    def test_con_varias_versiones_de_la_pregunta_cuenta_la_que_mas_se_parece(self):
        repo.indexar(self.raiz, embeber_falso)
        primero = repo.buscar(self.raiz, ["¿dónde está el stock?", "where is the inventario?"], embeber_falso, k=1)[0]
        self.assertEqual(primero.archivo, "src/stock.dart")

    def test_los_documentos_no_desplazan_al_codigo_y_se_agrega_el_mejor(self):
        (self.raiz / "PLAN.md").write_text("factura factura factura factura factura")
        (self.raiz / "NOTAS.md").write_text("inventario")
        repo.indexar(self.raiz, embeber_falso)
        archivos = [r.archivo for r in repo.buscar(self.raiz, "factura", embeber_falso, k=1)]
        self.assertEqual(archivos, ["src/facturas.py", "PLAN.md"])

    def test_buscar_sin_indice_avisa(self):
        with self.assertRaises(FileNotFoundError):
            repo.buscar(self.raiz, "x", embeber_falso)

    def test_preguntar_pasa_los_trozos_al_modelo_y_cita_las_fuentes(self):
        repo.indexar(self.raiz, embeber_falso)
        vistos = []
        texto = repo.preguntar(self.raiz, "¿dónde se emite la factura?", embeber_falso,
                               lambda t: vistos.append(t) or "En emitir().", k=1)
        self.assertEqual(len(vistos), 2)  # primero traduce la pregunta al inglés, luego responde
        self.assertIn("src/facturas.py:1", vistos[1])
        self.assertIn("def emitir():", vistos[1])
        self.assertTrue(texto.startswith("En emitir()."))
        self.assertIn("- src/facturas.py:1", texto)


if __name__ == "__main__":
    unittest.main()
