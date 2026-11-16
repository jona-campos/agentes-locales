# Plan: agentes restantes (1, 2, 3, 4 y 6)

Estado: aplicado parcialmente el 2026-11-15. Los cinco agentes están hechos y probados (detalle y cifras en `docs/BITACORA.md`).

## Pendiente

- Agente 1: la meta "el tipo coincide en 8 de 10" no se pudo medir porque tus repos no usan Conventional Commits. 2 de 10 diffs grandes quedaron sin mensaje. Falta que lo uses unos días y digas si el borrador sirve.
- Agente 4: `CBS.log` queda en 511 plantillas, sobre la meta de 200. Decidir si vale la pena Drain3.
- Agregar `agentes/` al `PATH` para llamar a los comandos sin ruta (cambia tu configuración; no se hizo).
- El revisor de seguridad sigue llamando a Ollama por `localhost` (2 s de más por llamada en Windows).

El agente 5 (audios) ya está hecho: `2026-11-15-agente-audios-aplicado-completamente-2026-11-15.md`.

## Objetivo

Cinco comandos que corren en la laptop con Ollama, sin que el código, los logs ni los diffs salgan del equipo.

| # | Comando | Qué hace | Éxito |
|---|---|---|---|
| 6 | (hook de git) | Bloquea el commit si lo preparado trae un secreto | Un commit con una clave de prueba se rechaza; uno limpio pasa en menos de 2 s |
| 1 | `commit sugerir` / `commit changelog` | Propone un mensaje Conventional Commits desde `git diff --staged`; arma el changelog desde `git log` | En 10 diffs reales, el tipo (`feat`, `fix`...) coincide con el tuyo en 8 o más; responde en menos de 30 s |
| 4 | `logs resumir <archivo>` | Agrupa las líneas repetidas en plantillas y el modelo explica las raras y los errores | Un log de 50 000 líneas queda en menos de 200 plantillas y el resumen nombra el error plantado |
| 2 | `pruebas esqueleto <archivo>` | Escribe un archivo de pruebas con un caso por función pública, que falla hasta que lo completes | El archivo generado compila y cada prueba falla con "pendiente" (Python con `unittest`, Dart con `flutter test`) |
| 3 | `repo indexar` / `repo preguntar "<pregunta>"` | Búsqueda semántica local sobre un repositorio y respuesta con archivo y línea | En 10 preguntas sobre un proyecto privado, el archivo correcto sale entre los 5 primeros en 8 o más |

## Qué ya existe (se reutiliza)

- Ollama en la GPU Arc con `qwen2.5-coder:7b` (13,4 tok/s) y `qwen3:4b`.
- En `revisor-seguridad/revisor/`: `cliente_ollama()` (urllib, JSON con esquema, temperatura 0), `interpretar()` con reintento, la lista `EXCLUIR` de carpetas generadas y el tapado de secretos antes de mandar texto al modelo.
- gitleaks 8.30.1 instalado. `pre-commit` y `git-cliff` no están instalados.
- Convenciones: pruebas con el modelo inyectado, medición contra casos con respuesta conocida, `docs/BITACORA.md`, `checklist.md`.

## Investigación de skills (find-skills, 2026-11-15)

`npx skills find` con seis consultas (`commit message`, `changelog`, `test generation`, `codebase search`, `log analysis`, `pre-commit secrets`). Lo más cercano: `conventional-changelog/conventional-changelog@conventional-commit-message` (1,1K instalaciones), `wshobson/agents@changelog-automation` (14,3K), `petrkindlmann/qa-skills@ai-test-generation` (1,5K), `aj-geddes/useful-ai-prompts@log-analysis` (678) y `github/awesome-copilot@secret-scanning` (4,7K). **No se instala ninguna.** Son instrucciones para Claude, y estos agentes corren con un modelo local sin Claude. Si quieres, de la primera se puede leer el formato del mensaje como referencia para el prompt (pasaría antes por `skillspector-security-gate`).

## Decisiones que necesito de ti

1. **Una carpeta para todos.** Recomiendo `agentes/` con un módulo por agente, un `modelo.py` común y un `.cmd` por comando. Solo biblioteca estándar de Python, sin entorno virtual. El revisor no se toca; el cliente de Ollama (unas 20 líneas) se copia a `modelo.py` en vez de reorganizar el revisor. El agente de audios iría aquí también, en lugar de `agente-audios/`.
2. **Hook anti-secretos: global o por repositorio.** Recomiendo global con `git config --global core.hooksPath`: protege todos tus repos de una vez, incluidos los futuros. Cambia tu configuración de git, así que lo ejecuto solo con tu permiso. Contra: los hooks de `.git/hooks` de cada repo dejan de correr, por eso el script encadena al `pre-commit` local si existe. Sin el framework `pre-commit` (habría que instalarlo y poner un archivo en cada repo); gitleaks ya trae `gitleaks git --pre-commit --staged --redact`.
3. **Changelog sin instalar nada.** Recomiendo unas 20 líneas que agrupan `git log` por tipo de commit. Alternativa: instalar `git-cliff` con winget, que da más formato del que hace falta.
4. **Logs: plantillas con expresiones regulares.** Recomiendo empezar tapando números, fechas, IP, UUID y hexadecimales y contando con `Counter`. Si en la medición las plantillas salen fragmentadas, se pasa a Drain3 (dependencia nueva, licencia por verificar, con tu permiso).
5. **Explicador de repo: versión mínima propia.** Recomiendo trozos de ~60 líneas, embeddings con Ollama, vectores en SQLite y similitud de coseno en Python. Sirve hasta unos 10 000 trozos. La alternativa era adaptar codeqai, pero arrastra FAISS, Treesitter y LangChain en Windows y su licencia está sin verificar. De codeqai se recicla la idea de mostrar archivo y línea de cada trozo.
6. **Descargas.** Para el agente 3 hace falta un modelo de embeddings: `nomic-embed-text` (~274 MB, recomendado) o `bge-m3` (~1,2 GB, mejor con preguntas en español). Para audios, y opcionalmente para el resumen de logs, `qwen2.5:7b-instruct` (~4,7 GB). Todo gratis; pido permiso antes de cada descarga.
7. **Esqueletos de pruebas en Dart.** Recomiendo pasarle al modelo el archivo completo y validar que la salida compila. `kvs_testsmith` queda como alternativa si el resultado es malo (habría que revisar su licencia y pasar el filtro de seguridad).

## Arquitectura

```
agentes/
  modelo.py        cliente de Ollama (generar y embeddings), inyectable en las pruebas
  commit.py        diff preparado → secretos tapados → modelo → "tipo(ámbito): resumen"
  logs.py          líneas → plantillas (regex + Counter) → raras y errores → modelo → resumen
  pruebas.py       Python: firmas con ast. Dart: archivo completo → modelo → archivo de pruebas
  repo.py          indexar: trozos → embeddings → SQLite en <repo>/.agentes/. preguntar: top 5 → modelo
  ganchos/pre-commit   script de gitleaks (sin modelo)
  tests/
```

- `commit sugerir` solo imprime el mensaje. No hace el commit.
- Diffs grandes: se manda `git diff --stat` completo y un tope de líneas por archivo.
- Antes de mandar un diff o un log al modelo se tapan los literales que parecen secretos, igual que en el revisor.
- El modelo no inventa rutas: `repo preguntar` solo cita trozos que salieron de la búsqueda, y `pruebas esqueleto` solo nombra funciones que `ast` encontró (en Python).

## Pasos (pruebas primero, skill `tdd`; un agente a la vez)

1. **Base:** carpeta `agentes/`, `modelo.py` con su prueba simulada.
2. **Agente 6:** script del hook, prueba en un repo temporal con una clave falsa plantada (se rechaza) y con un commit limpio (pasa). Instalación global solo con tu permiso.
3. **Agente 1:** `recortar_diff()`, `interpretar()` del mensaje (tipo válido, resumen de 72 caracteres o menos), CLI, changelog. Medición con 10 commits reales de tus repos.
4. **Agente 4:** `plantilla()` y `agrupar()` con un log de ejemplo, selección de raras y errores, resumen. Medición con un log real y uno con un error plantado.
5. **Agente 2:** Python (`ast` → esqueleto con `self.fail("pendiente")`), luego Dart. Se comprueba ejecutando el archivo generado.
6. **Agente 5:** su plan, cuando lo apruebes.
7. **Agente 3:** `trocear()`, índice en SQLite, `buscar()`, `preguntar()`. Medición con 10 preguntas de respuesta conocida.
8. Cada paso se anota en `docs/BITACORA.md` y se marca en `checklist.md`.

## Riesgos

- El modelo de 7B puede clasificar mal un commit o explicar mal un log. Por eso ningún comando actúa solo: proponen y tú decides.
- `core.hooksPath` global puede chocar con repos que usan husky u otros hooks. Husky fija su propia ruta por repo y esa gana; para el resto está el encadenado. Se deshace con `git config --global --unset core.hooksPath`.
- El explicador puede traer trozos poco útiles con trozos de líneas fijas. La medición lo dirá; el paso siguiente sería cortar por funciones.
- Memoria: el modelo de embeddings y el de 7B se cargan uno tras otro, no a la vez.

## Fuera del alcance

Hacer commits o push automáticos, JavaScript en los esqueletos de pruebas, vigilar logs en tiempo real, interfaz gráfica, servidor MCP.
