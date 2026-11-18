# Formato del presupuesto (`presupuesto.json`)

Las cuatro skills se pasan un solo archivo JSON. Cada una lo lee, agrega lo suyo y lo deja listo para la siguiente.

```json
{
  "obra": {"nombre": "Pavimentación calle X", "clave": "LO-026000-001-2026", "ubicacion": "Hermosillo, Son.", "fecha": "2026-11-11"},
  "factores": {
    "indirectos_campo": 0.06,
    "indirectos_oficina": 0.08,
    "financiamiento": 0.012,
    "utilidad": 0.10,
    "cargos_adicionales": 0.005
  },
  "insumos": [
    {"clave": "MAT-CEM", "descripcion": "Cemento gris CPC 30R", "unidad": "ton", "tipo": "material", "costo": 3450.00, "fuente": "[[Obras/2025 Puente Río Sonora]]"}
  ],
  "catalogo": [
    {"tipo": "agrupador", "nivel": 1, "clave": "A", "descripcion": "PRELIMINARES"},
    {"tipo": "concepto", "clave": "A-01", "descripcion": "Trazo y nivelación...", "unidad": "m2", "cantidad": 120.5,
     "origen": "Plano A-01, hoja 2", "confianza": "alta",
     "matriz": [
       {"insumo": "MO-CUA-TOP", "cantidad": 0.004},
       {"insumo": "HE-MENOR", "porcentaje_mo": 0.03}
     ]}
  ]
}
```

## Reglas
- **`tipo` de insumo:** `material`, `mano_obra`, `herramienta`, `equipo` o `flete`.
- **Herramienta menor** y otros cargos que dependen de la mano de obra van en la matriz con `porcentaje_mo` en vez de `cantidad`. Se calculan sobre la mano de obra de esa matriz.
- **Agrupadores** (partidas y subpartidas) llevan `nivel` (1, 2, 3…), igual que en Opus. Los conceptos van debajo del agrupador al que pertenecen, en orden.
- **`confianza`** (`alta`, `media` o `baja`) y **`origen`** los llena la lectura de planos. Lo que tenga confianza baja sale en la hoja «Revisar».
- **`fuente`** de cada insumo es la obra de referencia en la bóveda del usuario. Si no hay fuente, el cálculo lo marca; nunca se inventa.
- **Factores:** si solo se tiene un porcentaje de indirectos, se puede usar `"indirectos"` en lugar de campo y oficina.

## Cálculo del precio unitario (cascada de obra pública)
```
CD  = materiales + mano de obra + herramienta + equipo + fletes
CI  = CD × (indirectos de campo + indirectos de oficina)
CF  = (CD + CI) × financiamiento
CU  = (CD + CI + CF) × utilidad
CA  = (CD + CI + CF + CU) × cargos adicionales
PU  = CD + CI + CF + CU + CA        (redondeado a 2 decimales)
Importe = PU × cantidad
```
Opus recalcula todo con su propia configuración de sobrecosto. Este cálculo sirve para revisar que lo importado cuadre. Si los totales no coinciden, lo primero es revisar que los porcentajes de Opus sean los mismos que los de `factores`.

## Campos que agregan los scripts
- **`origen: "Catálogo del concurso"`**: concepto importado del catálogo de la dependencia. Su cantidad no se cambia.
- **`cantidad_planos`, `origen_planos`, `confianza_planos`**: lo que salió de los planos para un concepto del concurso.
- **`dudas_junta_aclaraciones`**: diferencias entre catálogo y planos, y conceptos que aparecen en planos pero no en el catálogo.
- **`fuera_de_catalogo`**: conceptos que existían antes o salieron de planos pero no vienen en el catálogo del concurso.
- **`insumos[].historico`**: mediana, número de precios y obras de la base histórica con las que se comparó el costo.
