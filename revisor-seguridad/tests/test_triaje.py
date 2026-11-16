"""Triaje con el modelo: el modelo se simula con funciones que devuelven texto.

La prueba con Ollama real solo corre con REVISOR_OLLAMA=1 (tarda y necesita el modelo).
"""
import json
import os
import unittest

from revisor import hallazgos as h
from revisor import triaje as t
from tests.test_hallazgos import RAIZ, cargar

VALIDA = {"veredicto": "real", "severidad": "alta",
          "explicacion": "El nombre del usuario entra directo en la consulta SQL.",
          "arreglo": "Usa parámetros: db.execute('... WHERE nombre = ?', (nombre,))"}


def grupo_sqli():
    codigo = h.desde_bandit(cargar("bandit.json"), RAIZ) + h.desde_semgrep(cargar("semgrep.json"), RAIZ)
    return [g for g in h.agrupar(codigo) if g.archivo == "app.py" and g.linea_inicio <= 20 <= g.linea_fin][0]


class Fragmento(unittest.TestCase):
    def test_numera_y_marca_las_lineas_del_grupo(self):
        texto = t.fragmento(RAIZ, grupo_sqli(), margen=3)
        lineas = texto.splitlines()
        self.assertEqual(len(lineas), 2 + 3 + 3)  # líneas 16 a 23
        self.assertTrue(lineas[0].lstrip().startswith("16"))
        self.assertIn(">>", [l for l in lineas if "SELECT" in l][0])
        self.assertNotIn(">>", [l for l in lineas if "def producto" in l][0])

    def test_no_se_sale_del_archivo(self):
        g = h.Grupo("config.py", 4, 4)
        self.assertEqual(len(t.fragmento(RAIZ, g, margen=50).splitlines()), 8)


class Prompt(unittest.TestCase):
    def test_incluye_reglas_codigo_y_pide_json(self):
        g = grupo_sqli()
        p = t.prompt(g, t.fragmento(RAIZ, g))
        self.assertIn("app.py", p)
        self.assertIn("B608", p)
        self.assertIn("SELECT * FROM productos", p)
        self.assertIn("JSON", p)


class Interpretar(unittest.TestCase):
    def test_json_valido(self):
        self.assertEqual(t.interpretar(json.dumps(VALIDA))["veredicto"], "real")

    def test_json_entre_bloques_de_codigo(self):
        self.assertIsNotNone(t.interpretar("```json\n" + json.dumps(VALIDA) + "\n```"))

    def test_rechaza_lo_invalido(self):
        for malo in ("no es json", "{\"veredicto\": \"real\"}", json.dumps({**VALIDA, "veredicto": "quizas"}),
                     json.dumps({**VALIDA, "severidad": "critica"}), json.dumps({**VALIDA, "explicacion": ""}), "[]"):
            with self.subTest(malo):
                self.assertIsNone(t.interpretar(malo))


class Triar(unittest.TestCase):
    def test_respuesta_valida(self):
        r = t.triar(grupo_sqli(), RAIZ, lambda p: json.dumps(VALIDA))
        self.assertTrue(r.revisado)
        self.assertEqual((r.veredicto, r.severidad), ("real", "alta"))

    def test_el_modelo_no_puede_esconder_un_hallazgo_de_severidad_alta(self):
        g = grupo_sqli()
        self.assertEqual(g.severidad, "alta")
        fp = dict(VALIDA, veredicto="falso_positivo", severidad="baja", explicacion="Parece seguro.")
        r = t.triar(g, RAIZ, lambda p: json.dumps(fp))
        self.assertEqual((r.veredicto, r.severidad), ("dudoso", "alta"))
        self.assertIn("Parece seguro.", r.explicacion)

    def test_un_falso_positivo_de_severidad_baja_se_respeta(self):
        g = h.Grupo("app.py", 1, 1, [h.Hallazgo("bandit", "B403", "app.py", 1, 1, "baja", "import pickle")])
        fp = dict(VALIDA, veredicto="falso_positivo", severidad="baja")
        self.assertEqual(t.triar(g, RAIZ, lambda p: json.dumps(fp)).veredicto, "falso_positivo")

    def test_respuesta_rota_queda_sin_revisar_nunca_descartada(self):
        r = t.triar(grupo_sqli(), RAIZ, lambda p: "lo siento, no puedo")
        self.assertFalse(r.revisado)
        self.assertEqual(r.veredicto, "sin_revisar")
        self.assertEqual(r.severidad, grupo_sqli().severidad)

    def test_reintenta_una_vez(self):
        respuestas = iter(["basura", json.dumps(VALIDA)])
        self.assertTrue(t.triar(grupo_sqli(), RAIZ, lambda p: next(respuestas)).revisado)

    def test_tapa_secretos_aunque_el_modelo_los_copie(self):
        # pasó de verdad con qwen2.5-coder:7b: copió la contraseña de config.py:4 en su explicación
        g = h.Grupo("config.py", 4, 4, [h.Hallazgo("bandit", "B105", "config.py", 4, 4, "baja", "Possible hardcoded password")])
        eco = {**VALIDA, "explicacion": "La contraseña 'Tienda2026!Admin' está en el código.",
               "arreglo": "Quita Tienda2026!Admin y usa os.environ['ADMIN_PASSWORD']"}
        r = t.triar(g, RAIZ, lambda p: json.dumps(eco))
        self.assertNotIn("Tienda2026!Admin", r.explicacion + r.arreglo)
        self.assertIn("os.environ['ADMIN_PASSWORD']", r.arreglo)

    def test_tapa_secretos_de_lineas_vecinas_que_el_modelo_tambien_ve(self):
        g = h.Grupo("config.py", 5, 5, [h.Hallazgo("semgrep", "aws-access-token", "config.py", 5, 5, "alta", "AWS")])
        r = t.triar(g, RAIZ, lambda p: json.dumps({**VALIDA, "explicacion": "Hay también ghp_7Kq2Wm9Xr4Tz8Lp3Vn6Bd1Hs5Jf0Gc2Ya4Me."}))
        self.assertNotIn("ghp_7Kq2", r.explicacion)

    def test_no_tapa_texto_con_espacios(self):
        r = t.triar(grupo_sqli(), RAIZ, lambda p: json.dumps({**VALIDA, "explicacion": "La consulta SELECT * FROM productos WHERE nombre = usa el nombre."}))
        self.assertIn("SELECT * FROM productos", r.explicacion)

    def test_error_de_conexion_queda_sin_revisar(self):
        def falla(p):
            raise ConnectionError("Ollama apagado")
        r = t.triar(grupo_sqli(), RAIZ, falla)
        self.assertEqual(r.veredicto, "sin_revisar")
        self.assertIn("Ollama apagado", r.explicacion)


@unittest.skipUnless(os.environ.get("REVISOR_OLLAMA") == "1", "pon REVISOR_OLLAMA=1 para usar el modelo real")
class OllamaReal(unittest.TestCase):
    def test_sqli_es_real(self):
        r = t.triar(grupo_sqli(), RAIZ, t.cliente_ollama())
        self.assertTrue(r.revisado, r.explicacion)
        self.assertEqual(r.veredicto, "real")


if __name__ == "__main__":
    unittest.main()
