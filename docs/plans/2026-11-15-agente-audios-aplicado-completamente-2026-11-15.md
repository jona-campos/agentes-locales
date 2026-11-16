# Plan: agente 5, transcribir y resumir audios

Estado: aprobado el 2026-11-15 (plan y descarga de qwen2.5:7b-instruct). Aún no hay código del agente.

## Objetivo

Un comando `audios resumir <audio>` que transcriba una nota de voz en local y deje un resumen en español, sin que el audio ni el texto salgan de la laptop.

**Éxito:**
1. Con un audio de prueba deja `<audio>.transcripcion.md` y `<audio>.resumen.md` junto al archivo (o en una carpeta que se indique).
2. El resumen incluye: resumen corto, puntos clave, tareas o acuerdos y lista de palabras dudosas (nombres propios y términos técnicos).
3. Un audio de 10 minutos tarda menos de 10 minutos en total.
4. Sin internet funciona igual.

## Qué ya existe (se reutiliza, no se reescribe)

- Transcripción: `~/.claude/herramientas/transcripcion/transcribir.py` con `venv-ov`, Whisper medium en la GPU Arc (~36 s por minuto de audio). El agente la llama como proceso externo.
- Ollama con `qwen2.5-coder:7b` y `qwen3:4b`. Ambos son pobres para resumir texto en español: el primero está afinado para código y el segundo, en el plan 1, tardó 10 veces más.
- Convenciones del proyecto: carpeta propia con `revisor/`-style, pruebas con el modelo inyectado, `docs/BITACORA.md`, `checklist.md`.

## Investigación de skills (find-skills, 2026-11-15)

`npx skills find` devolvió opciones de baja confianza para este caso: `openclaw/openclaw@openai-whisper` (4,7K instalaciones, pero usa el CLI de Whisper y no OpenVINO), `theplasmak/faster-whisper` (2,1K, duplica lo que ya tenemos) y `deepgram/*` (nube, rompe el requisito de privacidad). **Ninguna se instala.** La transcripción ya está resuelta y los resúmenes no necesitan una skill.

## Revisión de proyectos a reciclar (solo lectura, 2026-11-15)

Fuente: la nota de memoria `agentes-reciclar-github`. Se revisaron con `gh` licencia, actividad y los prompts, sin instalar ni clonar nada.

- **`paberr/ownscribe`: se recicla.** MIT, 111 estrellas, último cambio 2026-08-14, no archivado. Sus prompts (`src/ownscribe/summarization/prompts.py`) son texto corto en inglés: secciones Resumen, Puntos clave, Tareas y Decisiones, salida en Markdown (no JSON). Se copia solo la idea y la estructura, traducida y adaptada a notas de voz; el origen se cita en el código y en la bitácora. Como solo se reciclan prompts (texto, sin código ejecutable), no hace falta pasar `skillspector-security-gate`; si se copiara código, sí.
- **`stenolabs/stenoai`:** MIT, 1383 estrellas, activo. Es una app de escritorio completa; no se usa.
- **Hushnote** (`peteonrails/hushnote`, MIT, 30 estrellas, solo Linux) y **transcriberapp** (`MabelMoncy/TranscriberAppServerless`, 9 estrellas): descartados, poco mantenidos o fuera de lo que necesitamos.

**Prueba con el audio de 169 s (mismo audio, prompt de ownscribe en español, Markdown):**
- `qwen2.5-coder:7b`: 29 s, resumen correcto pero corto; menciona Navidad y deja las tareas en "Ninguna" (acertado). Se saltó los pasajes finales.
- `qwen3:4b`: 248 s por la API de chat porque `think:false` no se respetó y el modelo escribió su razonamiento (más de 1000 palabras) antes del resultado. El resumen final salió bien, pero convirtió la frase mal transcrita "vayan refresques" en una tarea. Con `/api/generate` y JSON antes tardó 65 s. Conclusión: para qwen3 hay que usar `/api/generate` o quitar el bloque `<think>` (ownscribe lo hace con `clean_response()`).
- Lo que aprendimos: el formato Markdown de ownscribe funciona igual de bien que el JSON y es más simple (sin validar JSON ni reintentos). Ninguno de los dos modelos tiene la calidad que queremos; falta probar `qwen2.5:7b-instruct`.

**Cambios al plan por esto:**
- Se quita el troceo (map-reduce): los audios serán de 5 minutos como máximo (~800 palabras), caben en un solo contexto de 4096 tokens.
- Salida en Markdown con las secciones de ownscribe, no JSON. "Palabras dudosas" se calcula con una regla en código y se compara con la lista del modelo.
- Quitar `<think>...</think>` de la respuesta antes de guardar.

## Decisiones que necesito de ti

1. **Modelo para resumir.** Recomiendo `qwen2.5:7b-instruct` (~4,7 GB, gratis, buen español, misma velocidad que el que ya mides, ~13 tok/s). Alternativa: `llama3.1:8b` (~4,9 GB). Descarga de varios GB: pido tu permiso antes.
2. **Dónde viven los archivos.** Recomiendo una carpeta `agente-audios/` dentro de `agentes locales`, igual que `revisor-seguridad/`, con un `audios.cmd` de atajo.
3. **Audios largos.** Ya no aplica: el límite es de 5 minutos, así que no hay troceo. Si un audio pasa de ~1500 palabras, el agente avisa y no resume.

## Arquitectura

```
audios resumir <audio>
  1. transcribir   → llama a transcribir.py (medium gpu), guarda <audio>.transcripcion.md con tiempos
  2. trocear       → trozos de ~3000 palabras cortando en final de frase
  3. resumir       → modelo local por trozo → JSON {resumen, puntos, tareas, dudosas}; JSON inválido = un reintento, luego "sin resumir"
  4. unir          → si hay más de un trozo, un resumen final de los resúmenes
  5. escribir      → <audio>.resumen.md
```

- Python 3.12 en la biblioteca estándar (urllib para Ollama, subprocess para la transcripción). Sin dependencias nuevas.
- El modelo solo recibe texto transcrito, nunca inventa tiempos ni citas: las citas se toman de la transcripción.
- Las palabras dudosas salen de una regla en código (nombres propios y términos poco frecuentes) y no solo del modelo, porque el dictado es automático y falla justo ahí.

## Pasos (pruebas primero, con la skill `tdd`)

1. Estructura de carpetas, `README` breve y fixture: un audio corto de prueba y su transcripción esperada.
2. `trocear()`: prueba con texto largo; corta en frases y no pierde palabras.
3. `interpretar()`: valida el JSON del modelo (campos, tipos, reintento). El modelo se inyecta como en el revisor.
4. `resumir()`: un trozo y varios trozos, con el modelo simulado.
5. `transcribir()` como borde: llama al script real, con una prueba que se salta si no hay audio de prueba.
6. CLI `audios resumir` y `audios.cmd`.
7. Medición: audio real de 1 y de 10 minutos, tiempo total y revisión tuya del resumen.
8. Documentar en `docs/BITACORA.md` y actualizar `CLAUDE.md` global solo si tú lo apruebas.

## Riesgos

- Un modelo de 7B puede omitir un acuerdo o inventar una tarea. Mitigación: el resumen muestra la cita con su tiempo para poder verificarla, y se mide contra un audio con tareas conocidas.
- Dictado con errores en nombres. Mitigación: la lista de dudosas y confirmación contigo antes de actuar sobre ellas.
- Memoria: Whisper y el modelo de 7B no caben a la vez en la GPU (16 GB compartidos). Se ejecutan en serie, no en paralelo.

## Fuera del alcance

Diarización (quién habla), traducción, interfaz gráfica, subir resúmenes a servicios externos.

## Cierre (2026-11-15)

Estado: aplicado completamente, con estas diferencias respecto al plan:

- El agente vive en `agentes/audios.py` (con `audios.cmd` y `tests/test_audios.py`), no en `agente-audios/`.
- Sin troceo: el límite es de 5 minutos (se avisa por encima de 1500 palabras). Salida en Markdown, no JSON.
- Modelo: `qwen2.5:7b-instruct`. Prompt adaptado de paberr/ownscribe (MIT), afinado con 4 variantes sobre 3 audios.
- Palabras dudosas: descartadas como regla en código (sin diccionario ni confianza de Whisper solo daría falsos avisos). La transcripción completa se guarda junto al resumen.
- No se cambió el `CLAUDE.md` global.

Sin verificar: solo se probaron 3 audios (45, 66 y 169 s), ninguno de 5 minutos. El resumen aún puede torcer un detalle o tomar un error de transcripción como dato; hay que contrastar con la transcripción.
