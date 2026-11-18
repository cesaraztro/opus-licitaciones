#!/usr/bin/env python3
"""Agrega los insumos de una obra a la base histórica de precios.

Uso:
    # Desde un Excel o CSV exportado de Opus (listado de insumos)
    python indexar_historico.py insumos_puente_2025.xlsx --obra "Puente Río Sonora" --fecha 2025-03
           [--historico historico_precios.csv] [--hoja Insumos] [--columnas "clave=A,descripcion=B,unidad=C,costo=E"]

    # Desde un presupuesto ya terminado (cierra el ciclo: cada licitación alimenta la base)
    python indexar_historico.py presupuesto_calculado.json [--historico historico_precios.csv]

Si la obra ya estaba en la base, sus precios se reemplazan (no se duplican).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from opus_tabla import numero, tabla, utf8_en_consola, normalizar  # noqa: E402
import historico  # noqa: E402

TIPOS = {"mat": "material", "mano": "mano_obra", "m.o": "mano_obra", "herr": "herramienta",
         "equ": "equipo", "maq": "equipo", "flet": "flete"}


def tipo_de(texto):
    t = normalizar(texto)
    for prefijo, tipo in TIPOS.items():
        if t.startswith(prefijo):
            return tipo
    return t or ""


def main():
    utf8_en_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--obra")
    ap.add_argument("--fecha", help="AAAA-MM o AAAA-MM-DD de los precios")
    ap.add_argument("--historico", default="historico_precios.csv")
    ap.add_argument("--hoja")
    ap.add_argument("--columnas")
    args = ap.parse_args()

    ruta = Path(args.archivo)
    nuevos = []
    if ruta.suffix.lower() == ".json":
        p = json.loads(ruta.read_text(encoding="utf-8"))
        obra = args.obra or p.get("obra", {}).get("nombre")
        fecha = args.fecha or p.get("obra", {}).get("fecha")
        for ins in p.get("insumos", []):
            if ins.get("costo"):
                nuevos.append({"clave": ins["clave"], "descripcion": ins["descripcion"], "unidad": ins["unidad"],
                               "tipo": ins.get("tipo", ""), "costo": float(ins["costo"])})
    else:
        obra, fecha = args.obra, args.fecha
        filas, _ = tabla(ruta, ("clave", "descripcion", "unidad", "costo", "tipo"), ("descripcion", "unidad", "costo"),
                         hoja=args.hoja, columnas=args.columnas)
        for f in filas:
            costo = numero(f.get("costo"))
            desc = " ".join(str(f.get("descripcion") or "").split())
            if not desc or not costo:
                continue
            nuevos.append({"clave": str(f.get("clave") or "").strip(), "descripcion": desc,
                           "unidad": str(f.get("unidad") or "").strip(), "tipo": tipo_de(f.get("tipo")), "costo": costo})
    if not obra or not fecha:
        sys.exit("Falta el nombre de la obra o la fecha de los precios (--obra y --fecha).")
    try:
        historico.a_fecha(fecha)
    except (ValueError, TypeError):
        sys.exit(f"Fecha no válida: {fecha}. Usa AAAA-MM o AAAA-MM-DD.")
    if not nuevos:
        sys.exit("No encontré insumos con costo en el archivo.")

    base = [f for f in historico.cargar(args.historico) if f["obra"] != obra]
    reemplazados = len(historico.cargar(args.historico)) - len(base)
    for n in nuevos:
        n.update({"obra": obra, "fecha": fecha})
    historico.guardar(args.historico, base + nuevos)

    print(f"Obra: {obra} ({fecha})")
    print(f"Insumos agregados: {len(nuevos)}" + (f" (reemplazan {reemplazados} anteriores)" if reemplazados else ""))
    obras = {f['obra'] for f in base + nuevos}
    print(f"Base histórica: {len(base) + len(nuevos)} precios de {len(obras)} obras → {args.historico}")


if __name__ == "__main__":
    main()
