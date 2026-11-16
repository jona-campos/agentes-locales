import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from agentes import pruebas

FUENTE = '''
import os

def total(precios, iva=0.13):
    return sum(precios) * (1 + iva)

def _interna():
    pass

async def cobrar(pedido):
    pass

class Caja:
    def __init__(self):
        self.abierta = False

    def abrir(self):
        self.abierta = True

    def _privado(self):
        pass

class _Oculta:
    def metodo(self):
        pass
'''

DART = '''
class Carrito {
  final List<double> _precios = [];
  void agregar(double precio) => _precios.add(precio);
  double total() => _precios.fold(0, (a, b) => a + b);
  void _recalcular() {}
}

double conIva(double monto) => monto * 1.13;
'''


class TestPublicos(unittest.TestCase):
    def test_python_lista_funciones_y_metodos_publicos(self):
        self.assertEqual(pruebas.publicos_python(FUENTE), ["total", "cobrar", "Caja.abrir"])

    def test_python_con_error_de_sintaxis_avisa(self):
        with self.assertRaises(ValueError):
            pruebas.publicos_python("def roto(:\n")


class TestCasos(unittest.TestCase):
    def test_sin_modelo_un_caso_por_miembro(self):
        self.assertEqual(pruebas.casos(["total"], FUENTE, None), {"total": ["pendiente"]})

    def test_con_modelo_se_descartan_nombres_inventados_y_se_limita_a_tres(self):
        def modelo(t):
            return json.dumps({"casos": [{"miembro": "total", "casos": ["lista vacía", "con IVA 0", "a", "b"]},
                                         {"miembro": "inventada", "casos": ["x"]}]})
        self.assertEqual(pruebas.casos(["total", "cobrar"], FUENTE, modelo),
                         {"total": ["lista vacía", "con IVA 0", "a"], "cobrar": ["pendiente"]})

    def test_si_el_modelo_falla_queda_el_esqueleto_basico(self):
        self.assertEqual(pruebas.casos(["total"], FUENTE, lambda t: "nada"), {"total": ["pendiente"]})

    def test_dart_los_miembros_los_propone_el_modelo_y_deben_estar_en_el_archivo(self):
        def modelo(t):
            return json.dumps({"casos": [{"miembro": "Carrito.total", "casos": ["carrito vacío"]},
                                         {"miembro": "conIva", "casos": []},
                                         {"miembro": "Carrito._recalcular", "casos": ["x"]},
                                         {"miembro": "Carrito.vaciar", "casos": ["x"]}]})
        self.assertEqual(pruebas.casos(None, DART, modelo),
                         {"Carrito.total": ["carrito vacío"], "conIva": ["pendiente"]})


class TestEsqueleto(unittest.TestCase):
    def test_python_el_archivo_corre_y_cada_prueba_falla_con_pendiente(self):
        codigo = pruebas.esqueleto_python("tienda", {"total": ["lista vacía", "con IVA 0"], "Caja.abrir": ["pendiente"]})
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "tienda.py"), "w", encoding="utf-8") as f:
                f.write(FUENTE)
            with open(os.path.join(d, "test_tienda.py"), "w", encoding="utf-8") as f:
                f.write(codigo)
            r = subprocess.run([sys.executable, "-m", "unittest", "test_tienda", "-v"], cwd=d,
                               capture_output=True, text=True)
        self.assertIn("Ran 3 tests", r.stderr)
        self.assertIn("failures=3", r.stderr)
        self.assertIn("test_total_lista_vacia", r.stderr)
        self.assertIn("AssertionError: pendiente", r.stderr)

    def test_dart_un_grupo_por_miembro_y_fail_pendiente(self):
        codigo = pruebas.esqueleto_dart({"Carrito.total": ["carrito 'vacío'"]}, "package:tienda/carrito.dart")
        self.assertIn("import 'package:tienda/carrito.dart';", codigo)
        self.assertIn("group('Carrito.total', () {", codigo)
        self.assertIn(r"test('carrito \'vacío\'', () {", codigo)
        self.assertIn("fail('pendiente');", codigo)
        self.assertEqual(codigo.count("{"), codigo.count("}"))


class TestRutas(unittest.TestCase):
    def test_destino_no_pisa_un_archivo_que_ya_existe(self):
        with tempfile.TemporaryDirectory() as d:
            fuente = os.path.join(d, "tienda.py")
            pathlib.Path(fuente).write_text(FUENTE, encoding="utf-8")
            self.assertEqual(pruebas.main(["esqueleto", fuente, "--sin-ia"]), 0)
            destino = os.path.join(d, "test_tienda.py")
            self.assertTrue(os.path.exists(destino))
            with self.assertRaises(SystemExit):
                pruebas.main(["esqueleto", fuente, "--sin-ia"])

    def test_dart_en_lib_va_a_test_con_import_de_paquete(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "lib", "src"))
            open(os.path.join(d, "pubspec.yaml"), "w").write("name: tienda\n")
            fuente = os.path.join(d, "lib", "src", "carrito.dart")
            self.assertEqual(pruebas.destino_dart(fuente),
                             (os.path.join(d, "test", "src", "carrito_test.dart"), "package:tienda/src/carrito.dart"))


if __name__ == "__main__":
    unittest.main()
