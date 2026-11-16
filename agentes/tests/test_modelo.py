import json
import unittest
from unittest import mock

from agentes import modelo


class Respuesta:
    def __init__(self, datos):
        self.datos = json.dumps(datos).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self.datos


class TestModelo(unittest.TestCase):
    def test_generar_manda_el_prompt_y_devuelve_la_respuesta(self):
        with mock.patch("urllib.request.urlopen", return_value=Respuesta({"response": "hola"})) as abrir:
            self.assertEqual(modelo.cliente_ollama()("di hola"), "hola")
        cuerpo = json.loads(abrir.call_args[0][0].data)
        self.assertEqual(cuerpo["prompt"], "di hola")
        self.assertNotIn("format", cuerpo)

    def test_generar_con_esquema_pide_json(self):
        with mock.patch("urllib.request.urlopen", return_value=Respuesta({"response": "{}"})) as abrir:
            modelo.cliente_ollama(esquema={"type": "object"})("x")
        self.assertEqual(json.loads(abrir.call_args[0][0].data)["format"], {"type": "object"})

    def test_embeddings_devuelve_un_vector_por_texto(self):
        with mock.patch("urllib.request.urlopen", return_value=Respuesta({"embeddings": [[1, 0], [0, 1]]})):
            self.assertEqual(modelo.cliente_embeddings()(["a", "b"]), [[1, 0], [0, 1]])

    def test_tapar_oculta_literales_que_parecen_claves(self):
        clave = "sk" + "9f8a7b6c5d4e3f2a1b0c"
        tapado = modelo.tapar(f'+API_KEY = "{clave}"\n+nombre = "configuracion"\n+TOKEN={clave}\n')
        self.assertNotIn(clave, tapado)
        self.assertIn("configuracion", tapado)
        self.assertEqual(tapado.count("[oculto]"), 2)


if __name__ == "__main__":
    unittest.main()
