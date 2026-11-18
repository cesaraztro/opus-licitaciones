---
name: opus-precios-unitarios
description: Calcula precios unitarios (matrices) de obra pública para Opus 2021 con la base histórica de precios del usuario y su bóveda de Obsidian. Arma cada matriz con materiales, mano de obra, herramienta, equipo y fletes, aplica indirectos, financiamiento, utilidad y cargos adicionales, y avisa cuando un costo se sale de lo histórico. Úsala cuando el usuario diga "calcula el precio unitario de...", "arma la matriz de...", "cuánto sale el m2/m3/ml de...", "aterriza los costos con obras de referencia", "saca los PU del catálogo", "cuánto nos costó el cemento en la obra pasada" o "mete esta obra a la base de precios".
---

# Precios unitarios para Opus

El resultado es un `presupuesto.json` con matrices completas y justificadas (formato en `ESQUEMA.md`, en esta misma carpeta). Los scripts están en `scripts/`, junto a este archivo; llámalos con su ruta completa.

## Fuentes de costos, en este orden
1. **Base histórica de precios** (`historico_precios.csv`): precios reales de obras del usuario exportados de Opus. Es la fuente más confiable.
2. **Bóveda de Obsidian** del usuario: notas de obras, criterios y rendimientos.
3. **Ninguna:** deja el insumo sin `fuente` y sin inventar costo. El cálculo lo marca para que el usuario lo confirme.

## Reglas
- **Cada costo lleva su `fuente`:** la obra de la base histórica o la nota `[[...]]` de la bóveda.
- **Las cuentas las hace el script.** Tú propones insumos, cantidades y rendimientos; `calcular_pu.py` suma, aplica la cascada de sobrecosto y redondea.
- **Los porcentajes de sobrecosto y la tasa de escalación son del usuario.** Si no los dio, pregúntaselos.
- **Usa las claves de insumo que el usuario ya tiene en Opus** (las de la base histórica), para que Opus no duplique insumos al importar.

## Pasos
1. **Base histórica.** La primera vez, y cada vez que el usuario exporte una obra de Opus:
   ```
   python scripts/indexar_historico.py insumos_obra.xlsx --obra "Puente Río Sonora" --fecha 2025-03 --historico historico_precios.csv
   ```
   El script encuentra solo los encabezados aunque el Excel traiga membrete. Si no los encuentra, pasa `--columnas "clave=A,descripcion=B,unidad=C,costo=E"`.
2. **Buscar precios y referencias:**
   ```
   python scripts/consultar_precios.py "concreto" "200" --unidad m3 --historico historico_precios.csv --escalacion 0.05
   python scripts/buscar_referencias.py "RUTA\A\LA\BOVEDA" "banqueta" "concreto"
   ```
   `consultar_precios` da cada precio con su obra y fecha, más mediana, mínimo y máximo (escalados a hoy si das `--escalacion`). `buscar_referencias` encuentra notas, rendimientos y criterios en la bóveda.
3. **Armar la matriz** de cada concepto en `presupuesto.json`:
   - Materiales con desperdicio incluido en la cantidad.
   - Mano de obra como 1 / rendimiento de la cuadrilla.
   - Herramienta menor con `porcentaje_mo`.
   - Equipo en horas y fletes si aplican.
   - Agrega a `insumos` los que falten, con `tipo`, `costo` y `fuente`.
4. **Calcular y revisar contra lo histórico:**
   ```
   python scripts/calcular_pu.py presupuesto.json --historico historico_precios.csv --escalacion 0.05
   ```
   Genera `presupuesto_calculado.json` y `presupuesto_pu.csv`. Avisa de:
   - insumos sin referencia;
   - costos que se alejan más de 25 % de la mediana histórica (ajustable con `--desviacion`);
   - insumos sin costo, sugiriendo el histórico.
   Si hay errores, corrígelos y vuelve a correrlo.
5. **Presentar al usuario:** tabla por concepto con clave, unidad, costo directo, PU y fuente, y debajo la lista de avisos. Pregunta antes de pasar a Opus.

## Siguiente paso
Con el visto bueno del usuario, `opus-liga-excel` genera el Excel y lo importa en Opus.
