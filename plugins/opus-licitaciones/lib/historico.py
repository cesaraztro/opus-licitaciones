"""Base histórica de precios de insumos (un CSV que crece con cada obra).

Columnas: obra, fecha (AAAA-MM-DD), clave, descripcion, unidad, tipo, costo
"""
import csv
import statistics
from datetime import date
from pathlib import Path

from opus_tabla import normalizar

CAMPOS = ["obra", "fecha", "clave", "descripcion", "unidad", "tipo", "costo"]


def cargar(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    for f in filas:
        f["costo"] = float(f["costo"])
    return filas


def guardar(ruta, filas):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        for f in sorted(filas, key=lambda x: (x["fecha"], x["obra"], x["clave"] or x["descripcion"])):
            w.writerow({k: f.get(k, "") for k in CAMPOS})


def a_fecha(texto):
    partes = [int(p) for p in str(texto).split("-")]
    while len(partes) < 3:
        partes.append(1)
    return date(*partes[:3])


def escalar(costo, fecha, tasa_anual, hoy=None):
    """Lleva un costo histórico a hoy con una tasa anual compuesta (0.05 = 5 % al año)."""
    if not tasa_anual:
        return costo
    hoy = hoy or date.today()
    anios = max(0.0, (hoy - a_fecha(fecha)).days / 365.25)
    return costo * (1 + tasa_anual) ** anios


def unidad_igual(a, b):
    return normalizar(a).replace(".", "").replace(" ", "") == normalizar(b).replace(".", "").replace(" ", "")


def similares(historico, clave=None, descripcion=None, unidad=None):
    """Primero por clave exacta; si no hay, por descripción normalizada y misma unidad."""
    if clave:
        por_clave = [f for f in historico if f["clave"] and f["clave"] == clave
                     and (not unidad or unidad_igual(f["unidad"], unidad))]
        if por_clave:
            return por_clave, "clave"
    if descripcion:
        d = normalizar(descripcion)
        por_desc = [f for f in historico if normalizar(f["descripcion"]) == d
                    and (not unidad or unidad_igual(f["unidad"], unidad))]
        if por_desc:
            return por_desc, "descripción"
    return [], None


def referencia(filas, tasa_anual=0.0, hoy=None):
    """Mediana (escalada) y rango de un grupo de precios históricos."""
    valores = [escalar(f["costo"], f["fecha"], tasa_anual, hoy) for f in filas]
    return {
        "n": len(valores),
        "obras": sorted({f["obra"] for f in filas}),
        "mediana": statistics.median(valores),
        "minimo": min(valores),
        "maximo": max(valores),
        "ultima_fecha": max(f["fecha"] for f in filas),
    }
