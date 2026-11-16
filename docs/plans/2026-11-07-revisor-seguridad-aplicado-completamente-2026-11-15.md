# Plan: revisor de seguridad local

Estado: aprobado el 2026-11-07. Pasos 1 a 7 hechos; falta decidir cómo tratar los falsos negativos del modelo y el paso 8 (proyecto real).

## Objetivo

Una herramienta de terminal que revise cualquier proyecto en busca de vulnerabilidades sin que el código salga de la laptop: escáneres tradicionales para encontrar y un modelo local pequeño para filtrar falsos positivos, explicar y proponer arreglos.

**Éxito:**
1. `revisor escanear <ruta>` deja un informe en `<ruta>/.revisor/` (Markdown para leer y JSON para la app futura).
2. En un proyecto de prueba con fallos plantados encuentra al menos el 80% de ellos, y el modelo descarta la mayoría de los falsos positivos sin descartar fallos reales.
3. Sin internet funciona igual (con las bases de datos y reglas descargadas antes).
4. Se puede lanzar en dos proyectos a la vez sin que se pisen.

## Requisitos

- Igual desde la terminal, desde una app futura o pidiéndoselo a Claude: la app solo leerá `.revisor/` y llamará al mismo comando.
- Privado: nada de telemetría. Semgrep con `--metrics=off` y reglas locales. osv-scanner en modo `--offline` con su base descargada.
- Hardware: Core Ultra 7 155H, Arc integrada y 16 GB compartidos. Modelo de 4 a 7B en Q4.
- Costo: cero. Todo es gratuito y de código abierto.

## Investigación previa (hecha el 2026-11-07)

- **vulnhuntr: descartado sin instalarlo.** Su README dice que solo analiza Python, que exige exactamente Python 3.10 y que con Ollama "no han tenido éxito" porque los modelos abiertos no estructuran bien la salida. Su último cambio es de febrero de 2025. Además deja que el modelo explore libremente, justo lo que este plan evita.
- **DefectDojo 3.5.0: funciona, pero es pesado.** Se levantó con Docker y se importó por API un escaneo de ejemplo de gitleaks: creó solo el proyecto y sus 2 hallazgos. Trae parsers para gitleaks, semgrep, osv-scanner y bandit (además de SARIF y un formato genérico). Costo medido: los 6 contenedores usan ~580 MB, pero Docker Desktop y su máquina virtual llegan a **~5,7 GB de RAM** (quedaron 0,4 GB libres), más ~2,1 GB de imágenes en disco.
- **Decisión:** el revisor genera sus propios informes, sin cambios en este plan. DefectDojo no puede correr a la vez que un modelo de 7B en 16 GB, así que queda como opción para la app (encenderlo solo para ver informes e importar por API), frente a un visor propio ligero. Se decide en el plan de la app.

## Arquitectura

```
revisor escanear <ruta>
  1. escáneres (en paralelo)  → gitleaks (secretos), semgrep (código), osv-scanner (dependencias), bandit (si es Python)
  2. normalizar               → una lista común: herramienta, regla, archivo, línea, severidad, fragmento
  3. triaje con el modelo     → por hallazgo: código ±20 líneas + regla → JSON {veredicto, explicación, arreglo}
  4. informe                  → .revisor/informe-<fecha>.md y .json
```

- **Lenguaje:** Python 3.12 en un venv propio, con la biblioteca estándar y `requests` solo si hace falta (para Ollama basta `urllib`).
- **Modelo:** Ollama como servicio de fondo con `qwen2.5-coder:7b` (medido en el paso 7: `qwen3:4b` fue 10 veces más lento y acertó menos, se descarta).
- **Por qué el modelo no busca solo:** los modelos pequeños inventan vulnerabilidades. Aquí solo opinan sobre lo que marcó un escáner, y su respuesta debe ser un JSON válido. Si no lo es, el hallazgo se queda como "sin revisar", nunca se descarta.
- **Varios proyectos a la vez:** cada ejecución es un proceso independiente que escribe en su propio `.revisor/`. Ollama atiende las peticiones en cola (`OLLAMA_NUM_PARALLEL=1`) para no llenar la memoria.

## Pasos (pruebas primero)

1. **Instalar** (con tu permiso; son programas de terceros): Ollama, gitleaks y osv-scanner (binarios oficiales de GitHub), y semgrep y bandit por pip en el venv. Comprobar si Semgrep funciona nativo en Windows y, si no, usarlo por Docker.
2. **Proyecto de prueba** `fixtures/vulnerable/` con fallos plantados y conocidos: una clave falsa, una inyección SQL, `eval` con entrada del usuario, una dependencia con CVE y algún falso positivo a propósito. Es la "verdad" contra la que se mide todo.
3. **Normalizar:** primero pruebas con salidas reales de cada escáner guardadas como fixtures y luego el código que las convierte a la lista común. **Además, agrupar por ubicación:** los escáneres repiten el mismo problema (53 hallazgos brutos para 16 fallos en el fixture). Agrupar por archivo y rango de líneas (inicio a fin de Semgrep) antes de llamar al modelo, para hacer una consulta por problema y no por hallazgo.
4. **Triaje:** prueba con el modelo simulado (respuestas guardadas), incluido un JSON roto. Después, el cliente real de Ollama.
5. **Informe:** prueba del Markdown y el JSON generados y luego el código.
6. **CLI** `revisor escanear <ruta> [--sin-ia] [--modelo X]`, con una prueba de punta a punta sobre `fixtures/vulnerable/`.
7. **Medición:** tiempo total, cuántos fallos plantados encuentra, cuántos falsos positivos filtra, comparando `qwen2.5-coder:7b` y `qwen3:4b`, y dos proyectos a la vez. **Con un segundo fixture `fixtures/vulnerable2/` con falsos positivos distintos**, que el prompt no haya visto: las reglas del prompt se escribieron mirando el primer fixture y medir solo con él inflaría el resultado. Línea base con el primero (paso 4, prompt 2): reales 13/13, falsos positivos 1/3, imports 2/2, ~16 s por grupo.
8. **Probarlo en uno de tus proyectos reales** (tú eliges cuál) y revisar el informe juntos.

Pendiente detectado en el paso 6: la base de osv-scanner y las reglas de Semgrep se descargaron una vez y envejecen. Hace falta una orden `revisor actualizar` (la única que usa internet) para refrescarlas.

Fuera de este plan, cada uno con su propio plan: la app para gestionar agentes, el hook de pre-commit y los otros agentes.

## Riesgos

- **Semgrep en Windows** puede ir limitado. Alternativa: Docker o WSL.
- **Reglas de Semgrep:** `--config auto` descarga reglas de internet en cada ejecución. Hay que bajarlas una vez y apuntar a la carpeta local.
- **osv-scanner** consulta osv.dev por defecto (manda nombres y versiones de paquetes, no código). Para ser 100% offline: `--offline` con la base descargada y actualizada de vez en cuando.
- **Velocidad:** con unos 10 a 25 tok/s, 50 hallazgos pueden tardar varios minutos. `--sin-ia` da el informe solo con los escáneres.
- **Memoria:** el modelo de 7B usa ~5 GB de los 16 GB compartidos. Con el navegador y Docker abiertos puede ir justo.
- **Calidad:** el modelo puede equivocarse al descartar. Por eso el informe muestra siempre el hallazgo original, y el veredicto del modelo es solo una sugerencia.

## Skills que pueden ayudar (opcional)

`npx skills find` encontró `trailofbits/skills@semgrep` (10.2K instalaciones) y `semgrep/skills@code-security` (2.7K). Me servirían a mí para escribir o ajustar reglas de Semgrep, no al agente local. Solo se instalarían después de pasarlas por SkillSpector y con tu visto bueno.

## Paso 8: arreglos que salieron de la prueba real (aprobado el 2026-11-15; ver `checklist.md` para lo hecho y lo pendiente)

En `Documents/github` el revisor sacó 9963 grupos (habría tardado más de 40 h con IA). Además, semgrep y osv no dieron nada. Arreglos, cada uno con su prueba primero:

1. **Exclusiones.** Agregar a `EXCLUIR`: `build`, `dist`, `.svelte-kit`, `.dart_tool`, `ephemeral`, `.data`, `.pytest_cache`, `coverage`, `Pods` y `.gradle`. Hacer que gitleaks también las respete con una configuración generada (`[extend] useDefault = true` más `[allowlist] paths`).
2. **bandit sin B101.** Un `assert` solo es un riesgo si se ejecuta con `python -O`, y en las pruebas es ruido (9161 hallazgos aquí).
3. **Tope para la IA.** Con más de 150 grupos, el modelo revisa primero los de severidad alta y media, hasta 150 (`--max-ia N`). El resto queda "sin_revisar" y se ve en el informe. Así una revisión no pasa de una hora.
4. **semgrep código 2.** Encontrar el archivo que lo rompe (probar subcarpeta por subcarpeta). Si el escáner falla, revisar archivo por archivo o excluirlo con aviso.
5. **Corte en el grupo 91.** Averiguar si fue Ollama, el tiempo de espera o el proceso.
6. **osv sin base de npm y Pub.** Lo resuelve `revisor actualizar` (ya pendiente). Es la única orden que usa internet y descarga las bases de npm, PyPI y Pub.

Después: repetir el escaneo de `Documents/github` y revisar el informe.
