# Checklist

## Revisor de seguridad local (docs/plans/2026-11-07-revisor-seguridad.md)

- [x] Visto bueno del plan
- [x] Probar DefectDojo y vulnhuntr (vulnhuntr descartado; DefectDojo funciona pero ocupa ~5,7 GB, queda para el plan de la app)
- [x] Instalar Ollama, gitleaks, osv-scanner, semgrep y bandit (con permiso)
- [x] Modelo `qwen2.5-coder:7b` descargado y probado (13,4 tok/s en GPU Arc)
- [x] Dejar Ollama en GPU de forma permanente (`OLLAMA_VULKAN=1`, `OLLAMA_IGPU_ENABLE=1` como variables de usuario)
- [x] Proyecto de prueba con fallos plantados (`fixtures/vulnerable`: 16 reales y 4 falsos positivos, con prueba de coherencia)
- [x] Reglas locales de Semgrep (python, javascript, generic/secrets) y base offline de osv-scanner
- [x] Salidas reales de los 4 escáneres guardadas en `tests/salidas/`
- [x] Normalizar las salidas de los escáneres y agruparlas por ubicación (`revisor/hallazgos.py`, 10 pruebas)
- [x] Triaje con el modelo (con JSON validado, reintento, "sin_revisar" si falla y secretos tapados)
- [x] Informe Markdown y JSON (`revisor/informe.py`, en `<proyecto>/.revisor/`, sin código fuente ni secretos)
- [x] CLI `revisor escanear` (`revisor.cmd`, escáneres en paralelo y sin red, avisos si algo falla)
- [x] Medición: aciertos, falsos positivos, tiempo y dos proyectos a la vez (qwen2.5-coder:7b gana; qwen3:4b descartado; en paralelo funciona)
- [x] Severidad alta nunca se pliega como falso positivo (queda "dudoso")
- [x] Falso negativo de `random` para tokens: regla en código (`_aleatorio_sensible`), queda "dudoso"
- [x] Prueba en un proyecto real (hecha en `Documents/github`: salieron 6 arreglos)
  - [x] Exclusiones de carpetas generadas, también en gitleaks
  - [x] bandit sin B101
  - [x] Tope de IA `--max-ia` (150 por defecto)
  - [x] semgrep código 2: no se repite en el escaneo completo (causa probable: carpetas generadas)
  - [x] Corte en el grupo 91: no se repite; 150 grupos con IA terminaron sin cortes
  - [x] `revisor actualizar` (bases de npm, PyPI y Pub para osv; reglas de Semgrep)
  - [x] Escaneo completo de `Documents/github` con IA (informe en `docs/ejemplos/informe-github-2026-11-15.md`)

## Agente 5: transcribir y resumir audios (docs/plans/2026-11-15-agente-audios-aplicado-completamente-2026-11-15.md)

- [x] Visto bueno del plan (agente 5)
- [x] Modelo qwen2.5:7b-instruct descargado y probado con un audio
- [x] Paso 1: `agentes/audios.py` con `resumir()`, fixture `tests/fixtures/nota_voz.txt` y 2 pruebas (47 en total pasan)
- [x] Paso 2: `transcribir()`, `informe()`, CLI `audios resumir` y `audios.cmd` (9 pruebas del agente); probado con tu audio de 169 s: 106 s en total
- [x] Paso 3: prompt afinado (v4: reglas de sentido, datos concretos y tareas); probado con 3 audios (169 s, 45 s, 66 s)
- [x] Regla de palabras dudosas descartada (ver bitácora)
- [x] Plan cerrado: aplicado completamente el 2026-11-15


## Agentes restantes: 1, 2, 3, 4 y 6 (docs/plans/2026-11-15-agentes-restantes-aplicado-parcialmente-2026-11-15.md)

- [x] Visto bueno del plan y de las 7 decisiones (hook global y `nomic-embed-text` aprobados aparte)
- [x] Base: carpeta `agentes/` y `modelo.py` (4 pruebas)
- [x] Agente 6: hook anti-secretos con gitleaks (3 pruebas; instalado global con `core.hooksPath`)
- [x] Agente 1: mensaje de commit y changelog (8 de 10 commits reales con mensaje)
  - [ ] Falta tu opinión tras usarlo: la meta del tipo no se pudo medir
- [x] Agente 4: analizador de logs (error plantado encontrado; `CBS.log` queda en 511 plantillas)
- [x] Agente 2: esqueletos de pruebas (Python y Dart, comprobados con `unittest` y `flutter test`)
- [x] Agente 3: explicador de repositorio (8 de 10 en una app Flutter propia)
  - [x] Medir en un proyecto privado (7 de 10; ~2 s por búsqueda con 6603 trozos; indexar tardó 21 min)

## Preparar el proyecto para GitHub (docs/plans/2026-11-15-publicar-en-github-aplicado-completamente-2026-11-15.md)

- [x] Visto bueno del plan y de las 6 decisiones
- [x] `.gitignore` y `.gitleaks.toml`
- [x] Quitar usuario de Windows, proyectos privados, claves y audios reales de lo que se publica
- [x] `README.md` raíz y `LICENSE` (MIT)
- [x] Pruebas (56 + 59) y gitleaks sobre lo preparado, sin hallazgos
- [x] `git init` en `main` y 69 archivos preparados (673 KB)
- [x] Primer commit en `main` (50f33ec, confirmado por el usuario)
- [x] Crear el repositorio público en GitHub y push (confirmado por el usuario)
