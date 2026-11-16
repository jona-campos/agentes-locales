import os
import random
import shutil
import string
import subprocess
import tempfile
import unittest

GANCHOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ganchos")


@unittest.skipUnless(shutil.which("git") and shutil.which("gitleaks"), "hace falta git y gitleaks")
class TestGancho(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(["git", "-c", f"core.hooksPath={GANCHOS}", "-c", "user.name=prueba",
                               "-c", "user.email=prueba@example.com", *args],
                              cwd=self.repo, capture_output=True, text=True)

    def preparar(self, nombre, texto):
        with open(os.path.join(self.repo, nombre), "w", encoding="utf-8") as f:
            f.write(texto)
        self.git("add", nombre)

    def test_commit_limpio_pasa(self):
        self.preparar("hola.py", "print('hola')\n")
        r = self.git("commit", "-q", "-m", "limpio")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_commit_con_clave_se_rechaza_y_no_la_muestra(self):
        # se genera al vuelo para no dejar nada con forma de clave en el repositorio
        clave = "ghp_" + "".join(random.choices(string.ascii_letters + string.digits, k=36))
        self.preparar("config.py", f'GITHUB_TOKEN = "{clave}"\n')
        r = self.git("commit", "-q", "-m", "con clave")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(clave, r.stdout + r.stderr)
        self.assertEqual(self.git("log", "--oneline").stdout, "")

    def test_encadena_al_hook_local_del_repo(self):
        local = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        with open(local, "w", newline="\n") as f:
            f.write("#!/bin/sh\necho hook-local\nexit 1\n")
        os.chmod(local, 0o755)
        self.preparar("hola.py", "print('hola')\n")
        r = self.git("commit", "-q", "-m", "limpio")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("hook-local", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
