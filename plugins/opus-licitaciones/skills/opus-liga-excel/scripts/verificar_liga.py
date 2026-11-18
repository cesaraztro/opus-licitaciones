#!/usr/bin/env python3
"""Revisa que el Excel de Liga Office esté completo y cuadre con el presupuesto.

Uso:
    python verificar_liga.py obra_liga.xlsx presupuesto_calculado.json [--formato formato_liga.json]

Checa:
  - columnas obligatorias sin celdas vacías (en agrupadores solo nivel, clave y descripción)
  - claves únicas en Catalogo e Insumos
  - cada matriz corresponde a un concepto y cada insumo de matriz existe en Insumos
  - la suma de importes del Excel es igual al total del JSON (tolerancia $0.05)
Sale con código 1 si algo falla.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    sys.exit("Falta openpyxl. Instálalo con:  python -m pip install openpyxl")

AQUI = Path(__file__).resolve().parent
CAMPOS_AGRUPADOR = {"nivel", "clave", "descripcion"}


def leer(ws, columnas, inicio):
    campos = [c["campo"] for c in columnas]
    filas = []
    for r, valores in enumerate(ws.iter_rows(min_row=inicio, max_col=len(campos), values_only=True), inicio):
        if all(v in (None, "") for v in valores):
            continue
        filas.append((r, dict(zip(campos, valores))))
    return filas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("presupuesto")
    ap.add_argument("--formato", default=str(AQUI / "formato_liga.json"))
    args = ap.parse_args()

    fmt = json.loads(Path(args.formato).read_text(encoding="utf-8"))
    p = json.loads(Path(args.presupuesto).read_text(encoding="utf-8"))
    wb = load_workbook(args.excel, data_only=True)
    inicio = fmt["fila_inicio"]
    errores = []

    datos = {}
    for clave, hoja in fmt["hojas"].items():
        if hoja["nombre"] not in wb.sheetnames:
            errores.append(f"Falta la hoja '{hoja['nombre']}'.")
            continue
        ws = wb[hoja["nombre"]]
        encabezados = [ws.cell(row=inicio - 1, column=i + 1).value for i in range(len(hoja["columnas"]))]
        esperados = [c["encabezado"] for c in hoja["columnas"]]
        if encabezados != esperados:
            errores.append(f"{hoja['nombre']}: encabezados {encabezados} ≠ {esperados}.")
        filas = leer(ws, hoja["columnas"], inicio)
        datos[clave] = filas
        obligatorias = [c["campo"] for c in hoja["columnas"] if c["obligatoria"]]
        for r, fila in filas:
            es_agrupador = clave == "catalogo" and fila.get("nivel") not in (None, "")
            for campo in obligatorias:
                if es_agrupador and campo not in CAMPOS_AGRUPADOR:
                    continue
                if clave == "catalogo" and not es_agrupador and campo == "nivel":
                    continue
                if fila.get(campo) in (None, ""):
                    errores.append(f"{hoja['nombre']} fila {r}: '{campo}' vacío.")

    if len(datos) < len(fmt["hojas"]):
        reportar(errores)  # sin las tres hojas no se puede cruzar nada

    claves_cat = [f["clave"] for _, f in datos["catalogo"]]
    claves_ins = [f["clave"] for _, f in datos["insumos"]]
    for nombre, claves in (("Catalogo", claves_cat), ("Insumos", claves_ins)):
        repetidas = {c for c in claves if claves.count(c) > 1}
        if repetidas:
            errores.append(f"{nombre}: claves repetidas {sorted(repetidas)}.")

    conceptos = {f["clave"] for _, f in datos["catalogo"] if f.get("nivel") in (None, "")}
    for r, f in datos["matrices"]:
        if f["clave_matriz"] not in conceptos:
            errores.append(f"Matrices fila {r}: la matriz {f['clave_matriz']} no es un concepto del catálogo.")
        if f["clave_insumo"] not in claves_ins:
            errores.append(f"Matrices fila {r}: el insumo {f['clave_insumo']} no está en Insumos.")
    sin_matriz = conceptos - {f["clave_matriz"] for _, f in datos["matrices"]}
    if sin_matriz:
        errores.append(f"Conceptos sin matriz: {sorted(sin_matriz)}.")

    total_excel = round(sum(float(f.get("importe") or 0) for _, f in datos["catalogo"]), 2)
    total_json = round(float(p.get("resumen", {}).get("total_sin_iva", 0)), 2)
    if abs(total_excel - total_json) > 0.05:
        errores.append(f"Total del Excel ${total_excel:,.2f} ≠ total del presupuesto ${total_json:,.2f}.")

    if errores:
        reportar(errores)
    print("OK: el Excel está completo y cuadra.")
    print(f"  {len(conceptos)} conceptos, {len(claves_ins)} insumos, {len(datos['matrices'])} renglones de matriz")
    print(f"  Total sin IVA: ${total_excel:,.2f}")


def reportar(errores):
    print(f"FALLÓ ({len(errores)}):")
    for e in errores:
        print("  -", e)
    sys.exit(1)


if __name__ == "__main__":
    main()
