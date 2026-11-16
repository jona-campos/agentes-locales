"""Agente 5: transcribe una nota de voz en local y la resume. Nada sale del equipo.

La estructura del prompt está adaptada de paberr/ownscribe (MIT):
https://github.com/paberr/ownscribe, src/ownscribe/summarization/prompts.py
"""
import argparse
import os
import re
import subprocess
import sys

from agentes.modelo import cliente_ollama, tapar

HERRAMIENTA = os.path.join(os.path.expanduser("~"), ".claude", "herramientas", "transcripcion")
PYTHON_OV = os.path.join(HERRAMIENTA, "venv-ov", "Scripts", "python.exe")
SCRIPT = os.path.join(HERRAMIENTA, "transcribir.py")
MAX_PALABRAS = 1500  # ~10 min de habla; el contexto de 4096 tokens no da para más

SISTEMA = ("Eres un asistente que toma notas de notas de voz. Escribes en español, con claridad y solo con lo "
           "que dice el texto. La transcripción es automática y puede tener errores.")

PROMPT = """Resume la siguiente nota de voz en notas estructuradas.

Reglas:
- Respeta el sentido exacto de lo que dice el hablante. Si hace una comparación o un contraste, preséntalo como tal y no lo conviertas en una recomendación.
- Incluye cada dato concreto que se diga: cifras, duraciones, nombres, lugares, fechas y versiones.
- No repitas ideas. No inventes nada que no esté en el texto.
- Si una frase no se entiende o parece mal transcrita, ignórala; no la conviertas en una tarea.

Secciones:
## Resumen
2-3 frases sobre de qué trata y qué quiere el hablante.

## Puntos clave
Viñetas, en el orden en que se dicen, cada una con su dato concreto.

## Tareas
Lo que el hablante pide, propone o decide hacer, aunque lo diga con otras palabras (por ejemplo "hay que dejar un resumen"). No cuentes consejos generales. Si no hay, escribe "Ninguna".

---

Transcripción:
{transcripcion}"""

_PENSAR = re.compile(r"<think>[\s\S]*?</think>\s*", re.IGNORECASE)


def resumir(transcripcion, modelo):
    """`modelo` es una función texto -> texto (cliente_ollama o una simulada)."""
    respuesta = modelo(SISTEMA + "\n\n" + PROMPT.format(transcripcion=transcripcion))
    return _PENSAR.sub("", respuesta).strip()


def transcribir(ruta, correr=subprocess.run):
    """Llama a la herramienta local (Whisper medium en GPU). Devuelve las líneas '[ tiempo] texto'."""
    r = correr([PYTHON_OV, SCRIPT, ruta, "medium", "gpu"], capture_output=True, text=True,
               encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode:
        raise RuntimeError(f"la transcripción falló: {r.stderr.strip()[-300:]}")
    lineas = [l for l in r.stdout.splitlines() if l.startswith("[")]
    if not lineas:
        raise RuntimeError("la transcripción no devolvió texto (¿audio vacío o sin voz?)")
    return lineas


def sin_tiempos(lineas):
    return " ".join(re.sub(r"^\[\s*[\d.]+\]\s*", "", l) for l in lineas)


def informe(texto, modelo):
    """Resumen en Markdown. Si el modelo falla o el audio es muy largo, lo dice y no lanza."""
    if len(texto.split()) > MAX_PALABRAS:
        return f"> Audio demasiado largo (más de {MAX_PALABRAS} palabras): no se resumió, solo se transcribió.\n"
    try:
        return resumir(tapar(texto), modelo) + "\n"
    except Exception as e:
        return f"> El modelo no respondió ({e}); solo queda la transcripción.\n"


def main(argv=None, correr=subprocess.run, modelo=None):
    p = argparse.ArgumentParser(prog="audios", description="Transcribe y resume una nota de voz en local.")
    sub = p.add_subparsers(dest="orden", required=True)
    r = sub.add_parser("resumir")
    r.add_argument("audio")
    r.add_argument("--sin-ia", action="store_true", help="solo transcribir")
    r.add_argument("--modelo", default="qwen2.5:7b-instruct")
    a = p.parse_args(argv)
    if not os.path.isfile(a.audio):
        sys.exit(f"No existe {a.audio}")
    try:
        lineas = transcribir(a.audio, correr)
    except RuntimeError as e:
        sys.exit(str(e))
    base = os.path.splitext(a.audio)[0]
    with open(base + ".transcripcion.md", "w", encoding="utf-8") as f:
        f.write("# Transcripción\n\n" + "\n\n".join(lineas) + "\n")
    print("Escribí", base + ".transcripcion.md")
    if a.sin_ia:
        return
    resumen = informe(sin_tiempos(lineas), modelo or cliente_ollama(a.modelo))
    with open(base + ".resumen.md", "w", encoding="utf-8") as f:
        f.write(resumen)
    print("Escribí", base + ".resumen.md")


if __name__ == "__main__":
    main()
