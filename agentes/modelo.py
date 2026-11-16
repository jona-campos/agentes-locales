"""Cliente de Ollama común a los agentes. Todo va a localhost: nada sale del equipo."""
import json
import re
import urllib.request

# 127.0.0.1 y no "localhost": en Windows prueba IPv6 primero y cada llamada tarda 2 s más
URL = "http://127.0.0.1:11434"
# las mismas carpetas generadas que salta el revisor de seguridad
EXCLUIR = {".revisor", ".agentes", ".venv", "venv", "node_modules", ".git", "build", "dist", ".svelte-kit",
           ".dart_tool", "ephemeral", ".data", ".pytest_cache", "coverage", "Pods", ".gradle", "__pycache__"}


def _pedir(ruta, cuerpo, timeout):
    pedido = urllib.request.Request(URL + ruta, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return json.loads(r.read())


def cliente_ollama(modelo="qwen2.5-coder:7b", esquema=None, timeout=300, contexto=4096):
    def consultar(texto):
        cuerpo = {"model": modelo, "prompt": texto, "stream": False,
                  # num_predict: tope de salida, para que una respuesta que no termina no agote el timeout
                  "options": {"temperature": 0, "num_ctx": contexto, "num_predict": 700}}
        if esquema:
            cuerpo["format"] = esquema
        return _pedir("/api/generate", cuerpo, timeout)["response"]
    return consultar


def cliente_embeddings(modelo="nomic-embed-text", timeout=300):
    def embeber(textos):
        return _pedir("/api/embed", {"model": modelo, "input": textos}, timeout)["embeddings"]
    return embeber


# shortcut: "secreto" = 10+ caracteres sin espacios con letras y números, entre comillas o tras CLAVE=;
# las claves solo con letras no se tapan. Para detectar de verdad está gitleaks (agente 6).
_SECRETO = re.compile(r"""(["'])([^\s"']{10,})\1|(?<=[A-Z_]=)([^\s"']{10,})""")


def tapar(texto):
    """Oculta lo que parece una clave antes de mandar un diff o un log al modelo."""
    def cambiar(m):
        valor = m.group(2) or m.group(3)
        if re.search(r"\d", valor) and re.search(r"[A-Za-z]", valor):
            return m.group(0).replace(valor, "[oculto]")
        return m.group(0)
    return _SECRETO.sub(cambiar, texto)
