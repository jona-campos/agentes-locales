"""`revisor actualizar`: la única orden que usa internet. Las pruebas simulan la ejecución de comandos."""
import getpass
import os
import unittest

from revisor import actualizar


class Falso:
    def __init__(self, fallan=()):
        self.llamadas, self.fallan = [], fallan

    def __call__(self, cmd, cwd=None):
        self.llamadas.append((cmd, cwd))
        if any(f in cmd[0] for f in self.fallan):
            return 1, "error simulado"
        # el escáner de osv necesita ver los manifiestos de los tres ecosistemas
        if "osv-scanner" in cmd[0]:
            ruta = cmd[-1]
            self.archivos = sorted(os.listdir(ruta))
            self.contenido = ""
            for a in self.archivos:
                with open(os.path.join(ruta, a), encoding="utf-8") as f:
                    self.contenido += f.read()
        return 0, ""


class Actualizar(unittest.TestCase):
    def test_actualiza_reglas_y_descarga_bases_de_los_tres_ecosistemas(self):
        f = Falso()
        avisos = actualizar.actualizar(f, rutas={"osv-scanner": "osv-scanner", "git": "git"})
        self.assertEqual(avisos, [])
        git = next(c for c, _ in f.llamadas if c[0] == "git")
        self.assertIn("pull", git)
        osv = next(c for c, _ in f.llamadas if "osv-scanner" in c[0])
        self.assertIn("--download-offline-databases", osv)
        self.assertEqual(f.archivos, ["package-lock.json", "pubspec.lock", "requirements.txt"])

    def test_no_manda_nada_del_usuario(self):
        f = Falso()
        actualizar.actualizar(f, rutas={"osv-scanner": "osv-scanner", "git": "git"})
        self.assertNotIn(getpass.getuser(), f.contenido)
        self.assertNotIn("Documents", f.contenido)

    def test_si_falla_un_paso_avisa_y_sigue_con_el_otro(self):
        f = Falso(fallan=("git",))
        avisos = actualizar.actualizar(f, rutas={"osv-scanner": "osv-scanner", "git": "git"})
        self.assertEqual(len(avisos), 1)
        self.assertIn("reglas", avisos[0])
        self.assertTrue(any("osv-scanner" in c[0] for c, _ in f.llamadas))

    def test_orden_en_la_cli(self):
        from revisor import cli
        self.assertEqual(cli.parser().parse_args(["actualizar"]).orden, "actualizar")


if __name__ == "__main__":
    unittest.main()
