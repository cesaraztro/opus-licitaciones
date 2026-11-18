---
name: lectura-planos
description: Lee planos de obra en PDF y saca conceptos con cantidades (números generadores) para un presupuesto de licitación en Opus. Prepara cada hoja en alta resolución con sus cotas en texto, anota cada medida con su plano y nivel de confianza, deja que un script haga las cuentas y, si hay catálogo del concurso, lista las diferencias para la junta de aclaraciones. Úsala cuando el usuario diga "lee estos planos", "cuantifica", "saca los generadores", "qué conceptos lleva esta obra", "cuánto concreto/acero/block lleva" o "revisa si las cantidades del catálogo cuadran".
---

# Lectura de planos y números generadores

Convierte planos en cantidades dentro de `presupuesto.json` (formato en `ESQUEMA.md`, en esta misma carpeta), con una hoja de números generadores que se puede auditar renglón por renglón. Los scripts están en `scripts/`, junto a este archivo; llámalos con su ruta completa.

## Reglas
- **Solo lo que está en el plano.** Cada medida lleva `ref` (eje, tramo o elemento) y cada concepto lleva `origen` (plano y hoja). Si una cota no se lee, no la supongas: pon `confianza: "baja"` y explica en `origen` qué falta.
- **Confianza:** `alta` si la cota está escrita (mejor aún si viene en el texto vectorial), `media` si sale de escala o de un detalle tipo, `baja` si es supuesta o ilegible.
- **No hagas cuentas.** Tú anotas medidas; `generadores.py` multiplica, descuenta vanos y suma.
- **DWG:** pide que lo exporten a PDF desde AutoCAD. Así se conservan las cotas como texto vectorial, que es exacto.

## Pasos
1. **Preparar los planos:**
   ```
   python scripts/preparar_planos.py planos/*.pdf --salida planos_preparados
   ```
   Por cada hoja deja una vista completa, acercamientos en cuadrícula (3×2, con traslape) y un `_texto.json` con todo el texto vectorial y su posición. Lee `indice.json` para saber qué plano es cada hoja, su escala, cuántas cotas trae y si es escaneada.
   - Ubica ejes y elementos en la vista completa; lee las cotas en los acercamientos.
   - **Cotas: primero `_texto.json`** (exacto), luego la imagen. Si una cota del texto y la imagen no coinciden, gana el texto.
   - Las hojas escaneadas solo se leen de imagen: confianza `media` como máximo.
2. **Revisar el juego completo** y decirle al usuario qué falta (por ejemplo, estructurales sin armado o instalaciones sin isométricos).
3. **Escribir `generadores.json`** con partidas y conceptos. El formato está en la cabecera de `scripts/generadores.py`. Dimensiones por unidad:
   - m2: largo × ancho (o largo × alto)
   - m3: largo × ancho × alto (o espesor)
   - ml: largo
   - pza / lote: piezas
   - kg: piezas × largo × peso_unitario
   - Vanos y huecos van con `"descontar": true`.
   - **Con catálogo del concurso:** usa sus mismas claves.
4. **Calcular:**
   ```
   python scripts/generadores.py generadores.json --presupuesto presupuesto.json
   ```
   - **Sin catálogo del concurso:** crea o actualiza el catálogo con las cantidades de planos.
   - **Con catálogo del concurso** (importado con `licitacion-opus`): las cantidades de la dependencia **no se tocan**. Las de planos se guardan como `cantidad_planos` y las diferencias mayores a 5 % (`--tolerancia`) salen como **dudas para la junta de aclaraciones**.
5. **Presentar al usuario:** primero los conceptos con confianza baja y las dudas de la junta, cada una con la pregunta concreta; después la tabla de cantidades.

## Siguiente paso
Con las cantidades revisadas, sigue con `opus-precios-unitarios`.
