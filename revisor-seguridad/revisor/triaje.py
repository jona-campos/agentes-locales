"""Le pide a un modelo local que juzgue cada grupo de hallazgos: real, falso positivo o dudoso.

El modelo solo opina sobre lo que marcaron los escáneres. Si su respuesta no es válida,
el grupo queda "sin_revisar" con la severidad del escáner: nunca se descarta en silencio.
"""
import json
import os
import re
import urllib.request
from dataclasses import dataclass

from revisor.hallazgos import ORDEN_SEVERIDAD

VEREDICTOS = ("real", "falso_positivo", "dudoso")

# "origen" y "analisis" van primero para que el modelo razone antes de dar el veredicto
ESQUEMA = {
    "type": "object",
    "properties": {
        "origen": {"type": "string", "enum": ["usuario", "constante", "secreto_en_codigo", "configuracion", "desconocido"]},
        "analisis": {"type": "string"},
        "veredicto": {"type": "string", "enum": list(VEREDICTOS)},
        "severidad": {"type": "string", "enum": ORDEN_SEVERIDAD},
        "explicacion": {"type": "string"},
        "arreglo": {"type": "string"},
    },
    "required": ["origen", "analisis", "veredicto", "severidad", "explicacion", "arreglo"],
}

INSTRUCCIONES = """Eres un revisor de seguridad de código. Los escáneres marcan por patrones y se equivocan seguido:
tu trabajo es separar lo real de lo que no lo es. Mira SOLO las líneas señaladas con >>.

Primero responde en "origen" de dónde viene el dato que llega a la función peligrosa en esas líneas:
"usuario" (petición, formulario, argumentos, archivo subido), "constante" (texto o número fijo escrito ahí mismo),
"secreto_en_codigo" (clave, token o contraseña escrita literal), "configuracion" o "desconocido".
Luego, en "analisis", explica en una frase si un atacante puede controlar algo en esas líneas.

Reglas:
- Si el origen es "constante", el veredicto es "falso_positivo": eval("2 + 2") o un comando fijo con shell=True no se pueden explotar.
- Un import solo (import pickle, import subprocess) es "falso_positivo": importar no ejecuta nada peligroso.
- MD5 o SHA1 para huellas de archivos, cachés o identificadores es "falso_positivo"; para contraseñas es "real".
- Datos del usuario que llegan sin validar a SQL, eval, shell, pickle, yaml.load o innerHTML son "real".
- Secretos escritos en el código, TLS sin verificar y debug activado en producción son "real".
- "dudoso" solo si de verdad no se puede saber con este fragmento.

Responde SOLO con el objeto JSON. "explicacion" (una o dos frases en español) y "arreglo"
(el cambio concreto en el código, o "" si es falso positivo). Nunca copies el valor de una clave, token o contraseña."""


@dataclass
class Triaje:
    veredicto: str  # real | falso_positivo | dudoso | sin_revisar
    severidad: str
    explicacion: str
    arreglo: str
    revisado: bool


def fragmento(raiz, grupo, margen=20):
    with open(os.path.join(raiz, grupo.archivo), encoding="utf-8", errors="replace") as f:
        lineas = f.read().splitlines()
    desde, hasta = max(1, grupo.linea_inicio - margen), min(len(lineas), grupo.linea_fin + margen)
    return "\n".join(f"{n:>4} {'>>' if grupo.linea_inicio <= n <= grupo.linea_fin else '  '} {lineas[n - 1]}"
                     for n in range(desde, hasta + 1))


def prompt(grupo, codigo):
    marcas = "\n".join(f"- {x.herramienta} {x.regla}: {x.mensaje}" for x in grupo.hallazgos)
    return (f"{INSTRUCCIONES}\n\nArchivo: {grupo.archivo} (líneas {grupo.linea_inicio}-{grupo.linea_fin})\n"
            f"Lo que dicen los escáneres:\n{marcas}\n\nCódigo:\n{codigo}\n")


def interpretar(texto):
    """Devuelve el dict validado o None si la respuesta no sirve."""
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin < inicio:
        return None
    try:
        d = json.loads(texto[inicio:fin + 1])
    except json.JSONDecodeError:
        return None
    if not (isinstance(d, dict) and d.get("veredicto") in VEREDICTOS and d.get("severidad") in ORDEN_SEVERIDAD
            and isinstance(d.get("explicacion"), str) and d["explicacion"].strip()
            and isinstance(d.get("arreglo"), str)):
        return None
    return d


def _literales_sin_espacios(codigo):
    """Textos entre comillas del fragmento que ve el modelo y que podrían ser claves o tokens."""
    # shortcut: "secreto" = 10+ caracteres sin espacios con letras y números; claves solo con letras no se tapan
    return {m.group(2) for m in re.finditer(r"([\"'])([^\s\"']{10,})\1", codigo)
            if re.search(r"\d", m.group(2)) and re.search(r"[A-Za-z]", m.group(2))}


def _tapar(texto, literales):
    # el prompt pide no copiar secretos, pero el modelo no siempre obedece: se tapa con código
    for s in literales:
        texto = texto.replace(s, "[oculto]")
    return texto


_ALEATORIO = re.compile(r"B311|random", re.I)
_SENSIBLE = re.compile(r"token|secret|secreto|passw|clave|contrase|otp|session|sesion|nonce|csrf|salt|reset|recuper|api_?key", re.I)


def _aleatorio_sensible(grupo, raiz):
    """True si el hallazgo es de aleatoriedad débil y la línea o su función (la `def` más cercana) hablan de secretos."""
    if not any(_ALEATORIO.search(x.regla) for x in grupo.hallazgos):
        return False
    try:
        with open(os.path.join(raiz, grupo.archivo), encoding="utf-8", errors="replace") as f:
            lineas = f.read().splitlines()
    except OSError:
        return False
    texto = lineas[max(grupo.linea_inicio - 1, 0):grupo.linea_fin]
    for l in reversed(lineas[max(grupo.linea_inicio - 16, 0):max(grupo.linea_inicio - 1, 0)]):
        if re.match(r"\s*(def |function |async function )|.*=>\s*\{?\s*$", l):
            texto.append(l)
            break
    return bool(_SENSIBLE.search("\n".join(texto)))


def triar(grupo, raiz, consultar, intentos=2, margen=8):
    """consultar(prompt) -> texto del modelo. Se inyecta para poder simularlo en las pruebas."""
    codigo = fragmento(raiz, grupo, margen)
    p = prompt(grupo, codigo)
    literales = _literales_sin_espacios(codigo)
    motivo = "el modelo no devolvió un JSON válido"
    for _ in range(intentos):
        try:
            d = interpretar(consultar(p))
        except Exception as e:  # Ollama apagado, timeout...: el grupo sigue en el informe
            motivo = f"no se pudo consultar el modelo: {e}"
            break
        if d:
            veredicto, severidad = d["veredicto"], d["severidad"]
            if veredicto == "falso_positivo" and grupo.severidad == "alta":
                # El modelo se equivoca a veces; un hallazgo grave no se pliega solo por su palabra.
                veredicto, severidad = "dudoso", "alta"
            explicacion = d["explicacion"].strip()
            if veredicto == "falso_positivo" and _aleatorio_sensible(grupo, raiz):
                # El 7B no ve el riesgo porque el atacante "no controla" el valor; adivinarlo basta.
                veredicto, severidad = "dudoso", "media"
                explicacion = "Aleatoriedad débil cerca de un secreto: no se descarta sin revisión humana. " + explicacion
            return Triaje(veredicto, severidad, _tapar(explicacion.strip(), literales),
                          _tapar(d["arreglo"].strip(), literales), True)
    return Triaje("sin_revisar", grupo.severidad, motivo, "", False)


def ollama_disponible(url="http://localhost:11434"):
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3):
            return True
    except OSError:
        return False


def cliente_ollama(modelo="qwen2.5-coder:7b", url="http://localhost:11434", timeout=300):
    def consultar(texto):
        cuerpo = json.dumps({"model": modelo, "prompt": texto, "stream": False, "format": ESQUEMA,
                             "options": {"temperature": 0, "num_ctx": 4096}}).encode()
        pedido = urllib.request.Request(f"{url}/api/generate", cuerpo, {"Content-Type": "application/json"})
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            return json.load(r)["response"]
    return consultar
