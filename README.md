# Agentes locales

[![pruebas](https://github.com/jona-campos/agentes-locales/actions/workflows/pruebas.yml/badge.svg)](https://github.com/jona-campos/agentes-locales/actions/workflows/pruebas.yml)

Siete herramientas de línea de comandos que usan modelos de lenguaje en mi laptop, con Ollama. El código, los logs, los diffs y los audios que procesan no salen del equipo.

Las hice para tareas que repito al programar y que no quería mandar a un servicio en la nube. Corren en una laptop con GPU integrada Intel Arc y 16 GB de memoria compartida, así que usan modelos de 7B o menos.

## Qué hay

| Comando | Qué hace | Carpeta |
|---|---|---|
| `revisor escanear <ruta>` | Corre gitleaks, bandit, Semgrep y osv-scanner, agrupa los hallazgos por ubicación y el modelo separa los reales de los falsos positivos | `revisor-seguridad/` |
| `commit sugerir` | Propone un mensaje Conventional Commits para lo que está en `git add` | `agentes/` |
| `commit changelog` | Agrupa los commits por tipo | `agentes/` |
| `logs resumir <archivo>` | Agrupa las líneas de un log en plantillas y explica los errores | `agentes/` |
| `pruebas esqueleto <archivo>` | Escribe un archivo de pruebas para Python o Dart con un caso por función pública, que falla hasta que lo completes | `agentes/` |
| `repo indexar` y `repo preguntar` | Búsqueda semántica sobre un repositorio y respuestas que citan archivo y línea | `agentes/` |
| `audios resumir <audio>` | Transcribe una nota de voz con Whisper y la resume | `agentes/` |
| hook `pre-commit` | Rechaza el commit si lo preparado trae una clave | `agentes/ganchos/` |

Ningún comando actúa solo. Proponen un mensaje, un informe o un archivo nuevo, y la decisión es de quien lo usa.

## Resultados medidos

Las cifras salen de `docs/BITACORA.md`, donde está cada medición con su fecha.

- Revisor de seguridad: en un proyecto de prueba con 16 fallos plantados, los escáneres detectan los 16 y el modelo marca como reales los 13 de código. En un segundo proyecto, 8 de 9. De los falsos positivos plantados acierta entre 1 de 3 y 2 de 4, así que el informe todavía pide revisión humana.
- Explicador de repositorio: en dos proyectos reales, 8 de 10 y 7 de 10 preguntas traen el archivo correcto entre los cinco primeros resultados. La primera versión acertaba 2 de 10, porque las preguntas en español encontraban la documentación en español y no el código en inglés. Subió al traducir la pregunta y buscar con las dos versiones.
- Logs: 78 453 líneas de un log de Windows quedan en 118 plantillas en menos de 3 segundos. En un log de 50 000 líneas con un error plantado, el modelo nombra el error, su línea y la causa en 18 segundos.
- Commits: 8 de 10 commits reales reciben un mensaje válido, en 7 a 35 segundos. Con diffs grandes el resumen es vago y a veces no sale.
- Esqueletos de pruebas: los archivos generados corren con `unittest` y con `flutter test`, y todas las pruebas fallan con "pendiente".
- Velocidad: `qwen2.5-coder:7b` genera unos 13 tokens por segundo en la GPU integrada.

Hay 115 pruebas automáticas: 56 en `agentes/` y 59 en `revisor-seguridad/`. El modelo se simula en casi todas, y las mediciones con el modelo real se hacen aparte.

## Requisitos

- Windows 10 u 11. No lo he probado en Linux ni en macOS.
- Python 3.12 o más nuevo.
- [Ollama](https://ollama.com) con `qwen2.5-coder:7b`, `qwen2.5:7b-instruct` (audios) y `nomic-embed-text` (búsqueda).
- [gitleaks](https://github.com/gitleaks/gitleaks) para el hook y el revisor.
- Solo para el revisor: [osv-scanner](https://github.com/google/osv-scanner), y un entorno virtual en `revisor-seguridad/.venv` con `semgrep` y `bandit`.
- Solo para audios: un script de transcripción con Whisper que no está en este repositorio. La ruta está al inicio de `agentes/audios.py`.

Los agentes de `agentes/` usan solo la biblioteca estándar de Python.

## Uso

Cada comando tiene un `.cmd` de atajo. Los de `agentes/` están descritos en [agentes/README.md](agentes/README.md).

```
agentes\commit.cmd sugerir
agentes\logs.cmd resumir C:\ruta\app.log
agentes\repo.cmd indexar
agentes\repo.cmd preguntar "¿Dónde se valida el token?"
revisor-seguridad\revisor.cmd escanear C:\ruta\proyecto
```

El revisor necesita las reglas de Semgrep, que no se incluyen aquí porque tienen su propia licencia:

```
git clone --depth 1 https://github.com/semgrep/semgrep-rules revisor-seguridad/reglas/semgrep-rules
revisor-seguridad\revisor.cmd actualizar
```

Pruebas:

```
python -m unittest discover -s agentes/tests -t .
cd revisor-seguridad
.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

## Qué es propio y qué es reutilizado

La detección de fallos de seguridad la hacen gitleaks, bandit, Semgrep y osv-scanner. La transcripción la hace Whisper sobre OpenVINO. Los modelos los sirve Ollama. El prompt de resumen de audios está adaptado de [paberr/ownscribe](https://github.com/paberr/ownscribe) (MIT).

Lo que escribí yo es lo que une esas piezas: la normalización y el agrupado de hallazgos, el triaje con el modelo y sus reglas en código, las plantillas de logs, el índice de búsqueda en SQLite, los esqueletos de pruebas y el hook.

## Límites conocidos

- Las claves de `revisor-seguridad/fixtures/` y de `revisor-seguridad/tests/` son falsas. Están plantadas para probar el revisor.
- Un modelo de 7B se equivoca. En el triaje de seguridad un hallazgo de severidad alta nunca se descarta solo: queda como dudoso.
- La búsqueda compara la pregunta contra todos los trozos en Python. Va bien hasta unos 10 000 trozos.
- Las plantillas de logs usan expresiones regulares. Con mensajes donde cambian varias palabras a la vez quedan más plantillas de las que debería.

## Documentación del proceso

`docs/plans/` tiene los planes de cada parte, con lo que quedó pendiente, y `docs/BITACORA.md` el registro de cada cambio y cada medición.

## Licencia

MIT. Ver [LICENSE](LICENSE).
