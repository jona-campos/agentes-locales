# Agentes locales

Comandos que corren con Ollama en esta laptop. Nada sale del equipo. Solo usan la biblioteca estándar de Python.

Para usarlos desde cualquier carpeta, agrega esta carpeta al `PATH` o llama al `.cmd` con su ruta completa.

| Comando | Qué hace |
|---|---|
| `commit sugerir` | Propone un mensaje Conventional Commits para lo que está en `git add`. No hace el commit. `--idioma inglés` para repos en inglés. |
| `commit changelog [rango]` | Agrupa los commits por tipo (`v1.0..HEAD`, por ejemplo). Sin modelo. |
| `logs resumir <archivo>` | Agrupa las líneas en plantillas y explica los errores y los mensajes raros. `--sin-ia` deja solo el conteo. |
| `pruebas esqueleto <archivo>` | Escribe `test_<nombre>.py` o `test/<ruta>_test.dart` con pruebas que fallan con "pendiente". No pisa archivos existentes. |
| `audios resumir <audio>` | Transcribe una nota de voz (Whisper medium en GPU) y deja `<audio>.transcripcion.md` y `<audio>.resumen.md` junto al audio. Máximo ~1500 palabras (unos 10 min). `--sin-ia` solo transcribe. |
| `repo indexar` | Crea o actualiza el índice en `<repo>/.agentes/` (se ignora solo en git). |
| `repo preguntar "<pregunta>"` | Responde citando archivo y línea. `--sin-ia` lista solo los trozos encontrados. |

## Hook anti-secretos

`ganchos/pre-commit` corre `gitleaks` sobre lo preparado y rechaza el commit si ve una clave. Está activo en todos los repos con:

```
git config --global core.hooksPath "<ruta de este repositorio>/agentes/ganchos"
```

- Falso positivo: `git commit --no-verify`.
- Quitarlo: `git config --global --unset core.hooksPath`.
- Si un repo tiene su propio `.git/hooks/pre-commit`, se ejecuta después de gitleaks.
- Si mueves esta carpeta, hay que volver a apuntar `core.hooksPath`.

## Modelos

- `qwen2.5-coder:7b` para los textos (`--modelo` lo cambia).
- `qwen2.5:7b-instruct` para `audios`.
- `nomic-embed-text` para la búsqueda de `repo`.

## Pruebas

```
python -m unittest discover -s agentes/tests -t .
```

Desde la carpeta `agentes locales`. El modelo se simula; solo las del hook usan `git` y `gitleaks` de verdad.
