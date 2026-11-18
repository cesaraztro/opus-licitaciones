#!/usr/bin/env python3
"""Consulta la base histórica de precios: qué costó un insumo en obras anteriores.

Uso:
    python consultar_precios.py "cemento" "cpc" [--unidad ton] [--historico historico_precios.csv]
           [--escalacion 0.05] [--max 15]

Busca los términos en clave y descripción (sin acentos ni mayúsculas). Con --escalacion
lleva cada precio a hoy con esa tasa anual (por ejemplo, la inflación de construcción
que el usuario use). Al final da mediana, mínimo y máximo por unidad.
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from opus_tabla import normalizar, utf8_en_consola  # noqa: E402
import historico  # noqa: E402


def main():
    utf8_en_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("terminos", nargs="+")
    ap.add_argument("--historico", default="historico_precios.csv")
    ap.add_argument("--unidad")
    ap.add_argument("--escalacion", type=float, default=0.0)
    ap.add_argument("--max", type=int, default=15)
    args = ap.parse_args()

    base = historico.cargar(args.historico)
    if not base:
        sys.exit(f"La base histórica está vacía o no existe: {args.historico}. Agrega obras con indexar_historico.py.")
    terminos = [normalizar(t) for t in args.terminos]
    hits = []
    for f in base:
        texto = normalizar(f"{f['clave']} {f['descripcion']}")
        if all(t in texto for t in terminos) and (not args.unidad or historico.unidad_igual(f["unidad"], args.unidad)):
            hits.append(f)
    if not hits:
        print("Sin resultados. Prueba con menos términos o sin --unidad.")
        return
    hits.sort(key=lambda f: f["fecha"], reverse=True)

    esc = args.escalacion
    print(f"{'Fecha':<11} {'Obra':<28} {'Clave':<12} {'Unidad':<6} {'Costo':>12}" + (f" {'A hoy':>12}" if esc else "") + "  Descripción")
    for f in hits[: args.max]:
        linea = f"{f['fecha']:<11} {f['obra'][:28]:<28} {f['clave'][:12]:<12} {f['unidad'][:6]:<6} {f['costo']:>12,.2f}"
        if esc:
            linea += f" {historico.escalar(f['costo'], f['fecha'], esc):>12,.2f}"
        print(linea + "  " + f["descripcion"][:70])
    if len(hits) > args.max:
        print(f"... y {len(hits) - args.max} más")

    print("\nResumen por unidad" + (f" (escalado a hoy al {esc:.1%} anual)" if esc else "") + ":")
    for unidad in sorted({f["unidad"] for f in hits}):
        grupo = [f for f in hits if f["unidad"] == unidad]
        valores = [historico.escalar(f["costo"], f["fecha"], esc) for f in grupo]
        print(f"  {unidad:<6} n={len(valores):<3} mediana {statistics.median(valores):,.2f}   "
              f"mín {min(valores):,.2f}   máx {max(valores):,.2f}   obras: {len({f['obra'] for f in grupo})}")


if __name__ == "__main__":
    main()
