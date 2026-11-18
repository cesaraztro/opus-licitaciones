---
name: licitacion-opus
description: Flujo completo de un presupuesto de licitación de obra pública en Opus 2021, del paquete del concurso al presupuesto importado. Importa el catálogo de la dependencia, encadena lectura-planos, opus-precios-unitarios y opus-liga-excel con una revisión del usuario entre cada paso, prepara las dudas para la junta de aclaraciones y al final alimenta la base histórica de precios. Úsala cuando el usuario diga "arma el presupuesto de esta licitación", "empieza la licitación de...", "de los planos a Opus", "importa el catálogo del concurso" o comparta un paquete de concurso.
---

# Licitación de principio a fin

Todo el flujo trabaja sobre un solo `presupuesto.json` en la carpeta de la licitación (formato en `ESQUEMA.md`, en esta misma carpeta). Cada paso tiene su skill; esta las ordena y marca dónde se detiene para que el usuario revise. Los scripts de esta skill están en `scripts/`, junto a este archivo.

| Paso | Cómo | Sale | Revisión del usuario |
|---|---|---|---|
| 1. Datos de la obra | Preguntar al usuario | `obra` y `factores` | Porcentajes de sobrecosto y tasa de escalación |
| 2. Catálogo del concurso | `scripts/importar_catalogo.py` | Catálogo con claves y cantidades de la dependencia | Partidas y conceptos completos |
| 3. Planos | Skill `lectura-planos` | Cantidades de planos y dudas para la junta | Dudas antes de la junta de aclaraciones |
| 4. Matrices | Skill `opus-precios-unitarios` | `presupuesto_calculado.json` | PU por concepto, avisos de costos |
| 5. A Opus | Skill `opus-liga-excel` | Presupuesto importado en Opus | Total de Opus contra la hoja Resumen |
| 6. Cerrar el ciclo | `indexar_historico.py` (de `opus-precios-unitarios`) | Precios de esta obra en la base histórica | — |

## Paso 2: importar el catálogo del concurso
```
python scripts/importar_catalogo.py "Catalogo de conceptos.xlsx" --presupuesto presupuesto.json
```
- Encuentra sola la fila de encabezados (CLAVE, DESCRIPCIÓN, UNIDAD, CANTIDAD), aunque el archivo traiga membrete.
- Toma como partidas las filas sin unidad ni cantidad.
- Une las descripciones que se partieron en varias filas.
- Si no detecta las columnas, pasa `--columnas "clave=A,descripcion=B,unidad=C,cantidad=D" --fila-encabezado 8`.
- Si el catálogo viene en PDF, conviértelo a Excel primero (el usuario suele tener la versión editable del concurso; pídesela).

## Reglas
- **No avances de paso sin el visto bueno del usuario.** Él firma la licitación.
- **El catálogo del concurso manda.** En obra pública a precios unitarios las cantidades las fija la dependencia. Los planos sirven para encontrar errores y preguntarlos en la junta de aclaraciones, no para cambiar cantidades.
- **El orden puede cambiar.** A veces el usuario aterriza costos con obras de referencia antes de ver los planos. Haz el paso 4 primero; los pasos 2 y 3 conservan las matrices.
- **Una carpeta por licitación**, con el número de concurso en el nombre. Ahí quedan JSON, CSV, Excel y planos preparados, para repetir o auditar el cálculo.
- **Al terminar**, haz el paso 6 y dile al usuario qué partes salieron de referencias viejas o de otra región.
