# opus-licitaciones

Plugin de Claude Code para armar presupuestos de licitación de obra pública en **Opus 2021 Presupuesto Programable**: del paquete del concurso al presupuesto importado en Opus, sin recapturar.

Hecho por AztroTech.

## Qué hace

| Skill | Qué resuelve |
|---|---|
| `licitacion-opus` | Lleva el flujo completo. Importa el catálogo de conceptos de la dependencia directo de su Excel, aunque traiga membrete y descripciones partidas en varias filas. |
| `lectura-planos` | Prepara cada plano PDF: vista completa, acercamientos para leer cotas y el texto vectorial exacto (cotas, escala, clave del plano). Calcula los números generadores y, contra el catálogo del concurso, saca las **dudas para la junta de aclaraciones**. |
| `opus-precios-unitarios` | Arma las matrices con la **base histórica de precios** de obras anteriores y la bóveda de Obsidian. Calcula los PU con la cascada de obra pública y **avisa cuando un costo se sale de lo histórico**. |
| `opus-liga-excel` | Genera el Excel que Opus importa con **Liga Office**, lo verifica y guía la importación. Computer use solo da unos clics, en lugar de capturar campo por campo. |

```
Catálogo del concurso ─┐
Planos PDF ────────────┼─► presupuesto.json ─► precios unitarios ─► Excel Liga Office ─► Opus
Base histórica ────────┘          ▲                                                       │
                                  └──────────── la obra terminada alimenta la base ◄──────┘
```

## Instalación

Requisitos: [Claude Code](https://code.claude.com) y Python 3.9 o más reciente.

1. Instalar las dependencias de Python:
   ```
   python -m pip install openpyxl pymupdf
   ```
2. Agregar el marketplace e instalar el plugin:
   ```
   claude plugin marketplace add cesaraztro/opus-licitaciones
   claude plugin install opus-licitaciones@aztrotech-opus
   ```
3. Abrir Claude Code y pedirle, por ejemplo: «arma el presupuesto de esta licitación» o «importa el catálogo del concurso».

Para recibir una versión nueva:
```
claude plugin marketplace update aztrotech-opus
```

## Cómo se usa en una licitación
1. Crea una carpeta para la licitación con el catálogo del concurso (Excel) y los planos (PDF).
2. Dile a Claude: «arma el presupuesto de esta licitación».
3. Revisa en cada paso lo que te muestra: dudas para la junta, avisos de costos y total contra Opus.
4. Al terminar, la obra entra sola a la base histórica de precios. Cada licitación hace más precisa la siguiente.

La primera vez, alimenta la base histórica con obras anteriores exportadas de Opus: «mete esta obra a la base de precios».

## Pruebas
```
python pruebas/correr_pruebas.py
```
Son 40 verificaciones con una obra **ficticia**. Corren solas en GitHub en cada cambio, en Windows y Linux. Cubren:
- catálogo del concurso con membrete;
- planos PDF, vectoriales y escaneados;
- generadores con descuentos de vanos;
- un PU calculado a mano (B-01: $479.07);
- base histórica, escalación y alertas;
- Excel para Liga Office y detección de Excel dañados.

## Antes de usarlo en una licitación real
- [ ] Confirmar que tu licencia de Opus 2021 trae **Liga Office**.
- [ ] Exportar una obra tuya a Excel y ajustar los encabezados en `plugins/opus-licitaciones/skills/opus-liga-excel/scripts/formato_liga.json`. El formato actual sigue la documentación de Ecosoft.
- [ ] Hacer una importación de prueba y guardar el ligado de columnas en Opus.
- [ ] Cargar 3 a 5 obras anteriores a la base histórica.
- [ ] Definir tus porcentajes de sobrecosto y la tasa de escalación.
- [ ] Prueba con una licitación ya cerrada: comparar contra el presupuesto final (meta: menos de 5 % de diferencia).

## Siguiente versión
Programa de obra (Gantt) a partir del catálogo y los rendimientos, e indirectos desglosados.

## Licencia
MIT. Ver [LICENSE](LICENSE).

## Estructura
```
.claude-plugin/marketplace.json        catálogo del marketplace
plugins/opus-licitaciones/
  .claude-plugin/plugin.json
  lib/                                 lectura de tablas y base histórica (compartido)
  skills/<skill>/SKILL.md + scripts/
pruebas/                               obra ficticia y pruebas
```
