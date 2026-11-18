---
name: opus-liga-excel
description: Pasa el presupuesto calculado a Opus 2021 sin recapturar. Genera un Excel con catálogo, insumos y matrices en el formato de Liga Office, lo verifica y guía la importación en Opus (Proyecto › Importar › Excel) con computer use, que solo hace unos clics y una revisión final. Úsala cuando el usuario diga "pásalo a Opus", "dalo de alta en Opus", "importa el catálogo", "captura los conceptos en Opus" o "genera el Excel para Opus".
---

# Transferencia a Opus con Liga Office

Opus 2021 importa desde Excel con **Liga Office**. Es mucho más rápido y seguro que capturar campo por campo con computer use: el Excel se arma en segundos y computer use solo hace la importación.

## Pasos
1. **Generar el Excel** desde el presupuesto calculado (sale de `opus-precios-unitarios`):
   ```
   python scripts/generar_liga.py presupuesto_calculado.json
   ```
   Crea `presupuesto_liga.xlsx` con las hojas Catalogo, Insumos, Matrices, Resumen y Revisar. La celda de inicio de los datos es A2 en las tres primeras hojas.
2. **Verificar** antes de tocar Opus:
   ```
   python scripts/verificar_liga.py presupuesto_liga.xlsx presupuesto_calculado.json
   ```
   Si falla, no importes: corrige y vuelve a generar.
3. **Mostrar al usuario la hoja Revisar.** Ahí están los insumos sin referencia y las cantidades con confianza baja. Importa solo con su visto bueno.
4. **Importar en Opus** (con computer use, o el usuario a mano):
   1. Crear la obra nueva en Opus, o abrir la de la licitación.
   2. Configurar los mismos porcentajes de sobrecosto que trae la hoja Resumen.
   3. Ir a Proyecto › Importar › Excel y abrir `presupuesto_liga.xlsx`.
   4. En el panel *Acciones de documentos*, ligar cada columna con su campo de Opus.
   5. Transferir con fila de inicio 2 y la hoja correspondiente. Primero Insumos, luego Catalogo y al final Matrices.
5. **Revisar en Opus:** captura de pantalla del total del presupuesto y comparación contra el «Total sin IVA» de la hoja Resumen. Si no cuadra, revisa primero los porcentajes de sobrecosto y después las unidades de los insumos.

## Ajustes al formato
Los encabezados y el orden de columnas viven en `scripts/formato_liga.json`. La primera vez que el usuario importe, compara contra una obra exportada desde su Opus y ajusta ese archivo (no el código). Después, guarda el ligado de columnas en Opus para reutilizarlo.

## Plan B
Si la licencia del usuario no trae Liga Office, la captura se hace con computer use concepto por concepto, usando el mismo `presupuesto_calculado.json` como fuente. Antes de cerrar, compara el total contra la hoja Resumen.
