# Plan: preparar el proyecto para GitHub

Estado: aplicado completamente el 2026-11-15. El repositorio se creó público directamente, por decisión del usuario (la recomendación 1 era pasar antes por privado), y los commits llevan el correo `noreply` de GitHub.

## Objetivo

Dejar `agentes locales` como un repositorio que se pueda subir a GitHub sin exponer nada privado y que alguien de fuera entienda en dos minutos.

**Éxito:** `git status` limpio tras el primer commit, gitleaks sin hallazgos fuera de los fixtures, las pruebas siguen pasando y ningún archivo publicado nombra tus repos privados, tus claves ni tu usuario de Windows.

## Qué encontré al revisar (2026-11-15)

- La carpeta pesa 389 MB y no es un repositorio git. Casi todo es `revisor-seguridad/.venv` y `revisor-seguridad/reglas/semgrep-rules`, que es un clon de terceros con su propio `.git` y su propia licencia.
- No hay `README`, `LICENSE` ni `.gitignore` en la raíz.
- gitleaks: fuera de `.venv` y de las reglas hay 11 hallazgos, todos claves falsas plantadas a propósito (`fixtures/vulnerable*`, `tests/salidas/`, `tests/test_triaje.py`). Ninguna clave real.
- `docs/ejemplos/informe-github-2026-11-15.md` es el informe real de tus repos, con 699 menciones a proyectos privados y sus fallos.
- `docs/BITACORA.md`, `checklist.md` y un plan nombran un proyecto privado, una app Flutter propia y una clave que quedó en el historial de un repo público.
- `revisor-seguridad/tests/salidas/*.json` y `agentes/README.md` llevan rutas con tu usuario de Windows.

- `agentes/tests/fixtures/nota_voz.txt` es la transcripción de una nota de voz real de otra persona (habla de su día y de la iglesia). No debe publicarse: se cambia por un texto inventado de la misma forma y se ajustan las pruebas de audios que la usan.

## Decisiones que necesito de ti

1. **Privado primero.** Recomiendo crear el repositorio privado, que lo revises en GitHub y pasarlo a público después. Gratis en los dos casos.
2. **Bitácora y planes.** Recomiendo publicarlos (muestran el proceso y las mediciones, que es lo que vale para el CV) cambiando las líneas que nombran proyectos privados y claves por descripciones genéricas. Alternativa: dejar `docs/` fuera.
3. **Informe real de tus repos.** Recomiendo excluirlo con `.gitignore`. Se queda en tu disco. El informe del fixture sí se publica.
4. **Licencia.** Recomiendo MIT para tu código. Las reglas de Semgrep no se redistribuyen: el README dice cómo clonarlas.
5. **Nombre y cuenta.** `agentes-locales` en la cuenta con la que `gh` ya tiene sesión.
6. **Primer commit en `main`.** Un repositorio nuevo no tiene otra rama donde empezar; necesito tu permiso explícito.

## Antes de publicar, fuera de este repo

La bitácora dice que una clave sigue en el historial de un repo público tuyo y que había que rotarla. Si no la rotaste, hazlo antes: aunque aquí no se publique la clave, sí conviene que esté resuelto.

## Pasos

1. `.gitignore`: `.venv/`, `__pycache__/`, `reglas/semgrep-rules/`, `.revisor/`, `.agentes/`, el informe real.
2. `.gitleaks.toml` con las rutas de los fixtures permitidas, para que tu propio hook anti-secretos deje pasar las claves falsas sin usar `--no-verify`.
3. Cambiar las rutas con tu usuario por una ruta genérica en `tests/salidas/` y en `agentes/README.md`, y correr las pruebas de los dos proyectos.
4. Cambiar en bitácora, checklist y plan las menciones a proyectos privados y claves (según la decisión 2).
5. `README.md` raíz: qué es, los siete comandos, requisitos, cifras medidas, qué es reutilizado (gitleaks, Semgrep, bandit, osv-scanner, Ollama, Whisper) y qué es propio. Pasado por `humanizer`. `LICENSE`.
6. `git init`, rama `main`, `git add` y revisar contigo la lista de archivos y que el diff no trae claves.
7. Commit (con tu confirmación) y, aparte, crear el repositorio y hacer push (con otra confirmación).

## Riesgos

- GitHub puede bloquear el push por las claves falsas de los fixtures (protección contra secretos). Si pasa, da un enlace para marcarlas como "usadas en pruebas"; ese clic es tuyo.
- Una vez público, lo subido puede quedar copiado aunque se borre. Por eso el paso por privado.

## Fuera del alcance

Demo en video, publicar en PyPI, CI en GitHub Actions, la aplicación para reunir los agentes.
