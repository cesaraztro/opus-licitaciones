#!/usr/bin/env python3
"""Convierte un presupuesto calculado en el Excel que Opus importa con Liga Office.

Uso:
    python generar_liga.py presupuesto_calculado.json [--salida obra_liga.xlsx] [--formato formato_liga.json]

El JSON debe venir de calcular_pu.py (necesita precio_unitario e importe).
Hojas que genera:
    Catalogo   agrupadores y conceptos con nivel, clave, descripción, unidad y cantidad
    Insumos    catálogo de insumos con tipo y costo
    Matrices   una fila por insumo de cada matriz (clave de matriz repetida)
    Resumen    totales para comparar contra Opus después de importar
    Revisar    avisos del cálculo y conceptos con confianza baja
Los encabezados y el orden de columnas salen de formato_liga.json.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Falta openpyxl. Instálalo con:  python -m pip install openpyxl")

AQUI = Path(__file__).resolve().parent
NEGRITA = Font(bold=True)
ENCABEZADO = PatternFill("solid", fgColor="D9D9D9")
AGRUPADOR = PatternFill("solid", fgColor="F2F2F2")
MONEDA = '#,##0.00'
CANTIDAD = '#,##0.000000'


def filas_catalogo(p):
    for fila in p["catalogo"]:
        if fila["tipo"] == "agrupador":
            yield {"nivel": fila["nivel"], "clave": fila["clave"], "descripcion": fila["descripcion"]}, True
        else:
            if "precio_unitario" not in fila:
                sys.exit(f"El concepto {fila['clave']} no tiene precio unitario. Corre primero calcular_pu.py.")
            yield {
                "nivel": "",
                "clave": fila["clave"],
                "descripcion": fila["descripcion"],
                "unidad": fila["unidad"],
                "cantidad": fila["cantidad"],
                "precio_unitario": fila["precio_unitario"],
                "importe": fila["importe"],
            }, False


def filas_insumos(p, tipos_opus):
    for ins in p["insumos"]:
        yield {
            "clave": ins["clave"],
            "descripcion": ins["descripcion"],
            "unidad": ins["unidad"],
            "tipo_opus": tipos_opus.get(ins["tipo"], ins["tipo"]),
            "costo": ins.get("costo") or 0,
        }, False


def filas_matrices(p):
    insumos = {i["clave"]: i for i in p["insumos"]}
    for fila in p["catalogo"]:
        if fila["tipo"] != "concepto":
            continue
        for item in fila.get("matriz") or []:
            ins = insumos[item["insumo"]]
            es_pct = "porcentaje_mo" in item
            yield {
                "clave_matriz": fila["clave"],
                "unidad_matriz": fila["unidad"],
                "clave_insumo": ins["clave"],
                "descripcion_insumo": ins["descripcion"],
                "unidad_insumo": "%mo" if es_pct else ins["unidad"],
                "composicion": item["porcentaje_mo"] if es_pct else item["cantidad"],
                "costo": "" if es_pct else (ins.get("costo") or 0),
                "importe": item.get("importe", ""),
            }, False


def escribir_hoja(ws, columnas, filas, fila_inicio):
    for c, col in enumerate(columnas, 1):
        celda = ws.cell(row=fila_inicio - 1, column=c, value=col["encabezado"])
        celda.font = NEGRITA
        celda.fill = ENCABEZADO
    r = fila_inicio
    for datos, es_agrupador in filas:
        for c, col in enumerate(columnas, 1):
            valor = datos.get(col["campo"], "")
            celda = ws.cell(row=r, column=c, value=valor)
            if col["campo"] in ("precio_unitario", "importe", "costo"):
                celda.number_format = MONEDA
            elif col["campo"] in ("cantidad", "composicion"):
                celda.number_format = CANTIDAD
            if es_agrupador:
                celda.font = NEGRITA
                celda.fill = AGRUPADOR
        r += 1
    ws.freeze_panes = ws.cell(row=fila_inicio, column=1)
    for c, col in enumerate(columnas, 1):
        ancho = 60 if "descripcion" in col["campo"] else max(12, len(col["encabezado"]) + 4)
        ws.column_dimensions[get_column_letter(c)].width = ancho
        if "descripcion" in col["campo"]:
            for fila in ws.iter_rows(min_row=fila_inicio, min_col=c, max_col=c):
                fila[0].alignment = Alignment(wrap_text=True, vertical="top")
    return r - fila_inicio


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("--salida")
    ap.add_argument("--formato", default=str(AQUI / "formato_liga.json"))
    args = ap.parse_args()

    p = json.loads(Path(args.entrada).read_text(encoding="utf-8"))
    fmt = json.loads(Path(args.formato).read_text(encoding="utf-8"))
    inicio = fmt["fila_inicio"]
    hojas = fmt["hojas"]

    wb = Workbook()
    wb.remove(wb.active)
    conteo = {}
    for clave, generador in (
        ("catalogo", filas_catalogo(p)),
        ("insumos", filas_insumos(p, fmt["tipos_opus"])),
        ("matrices", filas_matrices(p)),
    ):
        ws = wb.create_sheet(hojas[clave]["nombre"])
        conteo[clave] = escribir_hoja(ws, hojas[clave]["columnas"], generador, inicio)

    obra = p.get("obra", {})
    resumen = p.get("resumen", {})
    ws = wb.create_sheet("Resumen")
    datos = [
        ("Obra", obra.get("nombre", "")),
        ("Clave", obra.get("clave", "")),
        ("Ubicación", obra.get("ubicacion", "")),
        ("Fecha", obra.get("fecha", "")),
        ("Conceptos", resumen.get("conceptos", "")),
        ("Insumos", len(p["insumos"])),
        ("Total sin IVA", resumen.get("total_sin_iva", "")),
    ]
    for k, v in p.get("factores", {}).items():
        datos.append((f"Factor {k.replace('_', ' ')}", v))
    for r, (k, v) in enumerate(datos, 1):
        ws.cell(row=r, column=1, value=k).font = NEGRITA
        celda = ws.cell(row=r, column=2, value=v)
        if k == "Total sin IVA":
            celda.number_format = MONEDA
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 50

    ws = wb.create_sheet("Revisar")
    ws.cell(row=1, column=1, value="Pendiente de revisar antes de entregar").font = NEGRITA
    pendientes = list(resumen.get("avisos", []))
    if not pendientes:
        pendientes = ["Sin avisos."]
    for r, texto in enumerate(pendientes, 2):
        ws.cell(row=r, column=1, value=texto)
    ws.column_dimensions["A"].width = 110

    base = Path(args.entrada).with_suffix("")
    nombre = base.name.replace("_calculado", "")
    salida = Path(args.salida) if args.salida else base.with_name(nombre + "_liga.xlsx")
    wb.save(salida)

    print(f"Escrito: {salida}")
    for clave in ("catalogo", "insumos", "matrices"):
        print(f"  Hoja {hojas[clave]['nombre']}: {conteo[clave]} filas, celda de inicio A{inicio}")
    print(f"  Total sin IVA: ${resumen.get('total_sin_iva', 0):,.2f}")
    if resumen.get("avisos"):
        print(f"  {len(resumen['avisos'])} avisos en la hoja Revisar")


if __name__ == "__main__":
    main()
