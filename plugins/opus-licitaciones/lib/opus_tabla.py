"""Utilidades compartidas: leer tablas de Excel o CSV con encabezados en cualquier fila.

Los catálogos de concurso y las exportaciones de Opus casi nunca empiezan en A1:
traen membrete, nombre de la dependencia y notas arriba. Aquí se busca la fila
de encabezados por palabras clave y se devuelven filas como diccionarios.
"""
import csv
import re
import sys
import unicodedata
from pathlib import Path

SINONIMOS = {
    "clave": ("clave", "codigo", "cve", "no.", "num", "partida"),
    "descripcion": ("descripcion", "concepto", "insumo"),
    "unidad": ("unidad", "u.m.", "um", "unid"),
    "cantidad": ("cantidad", "cant"),
    "costo": ("costo", "precio unitario", "p.u.", "pu", "precio"),
    "tipo": ("tipo", "familia", "grupo"),
}


def utf8_en_consola():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def numero(valor):
    """Convierte '1,234.50', '$ 3,450', '12.5 m2' o 1234.5 en float. None si no hay número."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    m = re.search(r"-?[\d,]*\.?\d+", str(valor).replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def leer_filas(ruta, hoja=None):
    """Devuelve la tabla como lista de listas (valores crudos)."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".csv":
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            return [list(f) for f in csv.reader(fh)]
    try:
        from openpyxl import load_workbook
    except ImportError:
        sys.exit("Falta openpyxl. Instálalo con:  python -m pip install openpyxl")
    wb = load_workbook(ruta, data_only=True, read_only=True)
    ws = wb[hoja] if hoja else wb.worksheets[0]
    return [list(f) for f in ws.iter_rows(values_only=True)]


def campo_de(encabezado, campos):
    h = normalizar(encabezado)
    if not h:
        return None
    for campo in campos:
        for s in SINONIMOS[campo]:
            if h == s or h.startswith(s + " ") or (len(s) > 3 and s in h):
                return campo
    return None


def detectar_encabezados(filas, campos, obligatorios, max_filas=40):
    """Busca la fila con más encabezados conocidos. Devuelve (indice_fila, {campo: columna})."""
    mejor = (None, {})
    for i, fila in enumerate(filas[:max_filas]):
        mapa = {}
        for j, celda in enumerate(fila):
            campo = campo_de(celda, campos)
            if campo and campo not in mapa:
                mapa[campo] = j
        if all(c in mapa for c in obligatorios) and len(mapa) > len(mejor[1]):
            mejor = (i, mapa)
    if mejor[0] is None:
        faltan = ", ".join(obligatorios)
        sys.exit(f"No encontré la fila de encabezados (busqué columnas de: {faltan}). "
                 f"Indica las columnas a mano con --columnas.")
    return mejor


def mapa_manual(texto, campos):
    """--columnas "clave=A,descripcion=B,unidad=C,cantidad=D" → {campo: indice}."""
    mapa = {}
    for par in texto.split(","):
        campo, letra = par.split("=")
        campo, letra = campo.strip(), letra.strip().upper()
        if campo not in campos:
            sys.exit(f"Campo desconocido en --columnas: {campo}")
        idx = 0
        for ch in letra:
            idx = idx * 26 + (ord(ch) - 64)
        mapa[campo] = idx - 1
    return mapa


def tabla(ruta, campos, obligatorios, hoja=None, columnas=None, fila_encabezado=None):
    """Lee la tabla y devuelve lista de dicts {campo: valor} solo con filas no vacías."""
    filas = leer_filas(ruta, hoja)
    if columnas:
        mapa = mapa_manual(columnas, campos)
        inicio = (fila_encabezado or 1)  # fila de encabezado en base 1; datos empiezan después
    else:
        i, mapa = detectar_encabezados(filas, campos, obligatorios)
        inicio = i + 1
    salida = []
    for fila in filas[inicio:]:
        registro = {c: (fila[j] if j < len(fila) else None) for c, j in mapa.items()}
        if all(v in (None, "") for v in registro.values()):
            continue
        salida.append(registro)
    return salida, mapa
