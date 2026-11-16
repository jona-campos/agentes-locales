"""Arreglos del paso 8 (prueba real en Documents/github): exclusiones, B101 y tope de IA. Sin escáneres reales."""
import os
import re
import tempfile
import unittest

from revisor import cli, escaneo
from revisor.hallazgos import Grupo, Hallazgo


def grupo(n, sev):
    h = Hallazgo("semgrep", "r", f"f{n}.py", 1, 1, sev, "m", None)
    return Grupo(f"f{n}.py", 1, 1, [h])


class Exclusiones(unittest.TestCase):
    def test_incluye_las_carpetas_generadas_de_la_prueba_real(self):
        for d in ("build", "dist", ".svelte-kit", ".dart_tool", "ephemeral", ".data",
                  ".pytest_cache", "coverage", "Pods", ".gradle"):
            self.assertIn(d, escaneo.EXCLUIR)

    def test_config_de_gitleaks_extiende_la_base_y_excluye_rutas(self):
        toml = escaneo.config_gitleaks(["ephemeral", ".data"])
        self.assertIn("useDefault = true", toml)
        rutas = re.findall(r"'''(.*?)'''", toml)
        self.assertEqual(len(rutas), 2)
        for sep in ("/", "\\"):
            self.assertTrue(re.search(rutas[0], f"windows{sep}flutter{sep}ephemeral{sep}x.dart"))
            self.assertTrue(re.search(rutas[1], f"pos{sep}.data{sep}a.json"))
        self.assertFalse(re.search(rutas[0], "src/ephemeral_ok.py"))

    def test_gitleaks_usa_esa_configuracion(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = escaneo._tareas(tmp, tmp, escaneo.rutas_por_defecto())["gitleaks"][0]
            self.assertIn("--config", cmd)
            self.assertTrue(os.path.isfile(cmd[cmd.index("--config") + 1]))


class Bandit(unittest.TestCase):
    def test_no_reporta_assert(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = escaneo._tareas(tmp, tmp, escaneo.rutas_por_defecto())["bandit"][0]
        self.assertEqual(cmd[cmd.index("-s") + 1], "B101")


class TopeDeIA(unittest.TestCase):
    def test_elige_primero_alta_luego_media_y_respeta_el_tope(self):
        gs = [grupo(1, "baja"), grupo(2, "media"), grupo(3, "alta"), grupo(4, "baja"), grupo(5, "alta")]
        elegidos = cli.elegir_para_ia(gs, 3)
        self.assertEqual([g.archivo for g in elegidos], ["f3.py", "f5.py", "f2.py"])

    def test_con_menos_grupos_que_el_tope_van_todos(self):
        gs = [grupo(1, "baja"), grupo(2, "alta")]
        self.assertEqual(len(cli.elegir_para_ia(gs, 150)), 2)

    def test_tope_cero_no_usa_ia(self):
        self.assertEqual(cli.elegir_para_ia([grupo(1, "alta")], 0), [])

    def test_opcion_max_ia_existe_con_150_por_defecto(self):
        self.assertEqual(cli.parser().parse_args(["escanear", "x"]).max_ia, 150)
        self.assertEqual(cli.parser().parse_args(["escanear", "x", "--max-ia", "7"]).max_ia, 7)


if __name__ == "__main__":
    unittest.main()


class AleatoriedadDebil(unittest.TestCase):
    """Falso negativo del 7B: descartaba random.random() usado para un token de recuperación."""
    RAIZ2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "vulnerable2")
    FP = '{"origen":"constante","analisis":"a","veredicto":"falso_positivo","severidad":"baja","explicacion":"no","arreglo":""}'

    def triar(self, linea):
        from revisor import triaje
        h = Hallazgo("bandit", "B311", "servicio.py", linea, linea, "baja", "random no es criptográfico")
        return triaje.triar(Grupo("servicio.py", linea, linea, [h]), self.RAIZ2, lambda p: self.FP)

    def test_random_dentro_de_una_funcion_de_token_no_se_descarta(self):
        r = self.triar(49)  # def token_recuperacion(): return str(random.random())[2:]
        self.assertEqual(r.veredicto, "dudoso")
        self.assertIn("aleatoriedad", r.explicacion.lower())

    def test_random_para_elegir_un_tema_si_se_descarta(self):
        self.assertEqual(self.triar(61).veredicto, "falso_positivo")  # random.choice(TEMAS)
