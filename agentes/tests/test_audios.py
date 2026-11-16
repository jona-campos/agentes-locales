import os
import unittest

from agentes import audios

NOTA = os.path.join(os.path.dirname(__file__), "fixtures", "nota_voz.txt")


class TestResumir(unittest.TestCase):
    def setUp(self):
        with open(NOTA, encoding="utf-8") as f:
            self.texto = f.read()

    def test_manda_la_transcripcion_al_modelo_y_devuelve_el_markdown(self):
        recibido = []

        def modelo(prompt):
            recibido.append(prompt)
            return "## Resumen\nAlgo."

        self.assertEqual(audios.resumir(self.texto, modelo), "## Resumen\nAlgo.")
        self.assertIn("buenos días", recibido[0])

    def test_quita_el_razonamiento_del_modelo(self):
        modelo = lambda p: "<think>pienso...</think>\n\n## Resumen\nAlgo."
        self.assertEqual(audios.resumir(self.texto, modelo), "## Resumen\nAlgo.")


SALIDA = "dispositivo: GPU\nidioma: es duración: 5.0 s\n[   0.0] hola buenos días\n[   3.2] nos vemos el jueves\n"


class Proceso:
    def __init__(self, salida, codigo=0):
        self.stdout, self.stderr, self.returncode = salida, "falló", codigo


class TestTranscribir(unittest.TestCase):
    def test_se_queda_con_las_lineas_con_tiempo_y_llama_al_script_con_medium_gpu(self):
        llamadas = []
        lineas = audios.transcribir("nota.ogg", lambda cmd, **kw: llamadas.append(cmd) or Proceso(SALIDA))
        self.assertEqual(lineas, ["[   0.0] hola buenos días", "[   3.2] nos vemos el jueves"])
        self.assertEqual(llamadas[0][-3:], ["nota.ogg", "medium", "gpu"])

    def test_si_el_script_falla_lo_dice(self):
        with self.assertRaises(RuntimeError):
            audios.transcribir("nota.ogg", lambda cmd, **kw: Proceso("", 1))

    def test_sin_texto_avisa(self):
        with self.assertRaises(RuntimeError):
            audios.transcribir("nota.ogg", lambda cmd, **kw: Proceso("idioma: es\n"))

    def test_sin_tiempos_deja_solo_el_texto(self):
        self.assertEqual(audios.sin_tiempos(["[   0.0] hola", "[  3.2] adiós"]), "hola adiós")


class TestInforme(unittest.TestCase):
    def test_el_modelo_recibe_el_texto_tapado(self):
        clave = "tok" + "9f8a7b6c5d4e3f2a"
        vistos = []
        audios.informe(f'la clave es "{clave}"', lambda t: vistos.append(t) or "## Resumen\nok")
        self.assertNotIn(clave, vistos[0])

    def test_si_el_modelo_falla_devuelve_aviso_y_no_lanza(self):
        def roto(t):
            raise OSError("sin conexión")
        self.assertIn("no respondió", audios.informe("hola", roto))

    def test_un_audio_demasiado_largo_no_se_resume(self):
        llamado = []
        md = audios.informe("palabra " * (audios.MAX_PALABRAS + 1), lambda t: llamado.append(t))
        self.assertIn("demasiado largo", md)
        self.assertEqual(llamado, [])


if __name__ == "__main__":
    unittest.main()
