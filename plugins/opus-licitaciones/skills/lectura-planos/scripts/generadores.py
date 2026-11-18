#!/usr/bin/env python3
"""Calcula cantidades desde las medidas leídas en los planos (números generadores).

Claude lee los planos y anota medidas; este script hace la aritmética para que
ninguna cantidad salga de una cuenta mental.

Uso:
    python generadores.py generadores.json [--presupuesto presupuesto.json]

generadores.json:
{
  "partidas": [{"clave": "A", "nivel": 1, "descripcion": "PRELIMINARES"}],
  "conceptos": [
    {"clave": "A-01", "partida": "A", "descripcion": "Muro de block...", "unidad": "m2",
     "confianza": "media", "origen": "Plano A-02",
     "medidas": [
        {"ref": "Eje 1, A-D", "largo": 12.4, "alto": 2.7, "piezas": 1},
        {"ref": "Puertas P-1", "largo": 0.9, "alto": 2.1, "piezas": 3, "descontar": true}
     ]}
  ]
}
Dimensiones aceptadas: largo, ancho, alto (o espesor), peso_unitario. La cantidad de
cada renglón es el producto de las dimensiones presentes por las piezas.

Escribe:
    <base>_generadores.csv   hoja de números generadores (renglón por renglón)
    presupuesto.json         crea o actualiza el catálogo (agrupadores y conceptos con cantidad,
                             origen y confianza). Si el concepto ya existe conserva su matriz.
"""
import argparse
import csv
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DIMENSIONES = ("largo", "ancho", "alto", "espesor", "peso_unitario")
ESPERADAS = {"m": 1, "ml": 1, "m2": 2, "m3": 3, "pza": 0, "pieza": 0, "lote": 0, "jgo": 0, "sal": 0}


def d(v):
    return Decimal(str(v))


def calcular(gen):
    avisos, errores, renglones, conceptos = [], [], [], []
    for c in gen.get("conceptos", []):
        clave = c.get("clave")
        unidad = (c.get("unidad") or "").lower().replace("²", "2").replace("³", "3")
        medidas = c.get("medidas") or []
        if not medidas:
            errores.append(f"{clave}: sin medidas.")
            continue
        total = Decimal(0)
        for m in medidas:
            dims = [k for k in DIMENSIONES if m.get(k) not in (None, "")]
            esperadas = ESPERADAS.get(unidad)
            if esperadas is not None and unidad != "kg" and len([x for x in dims if x != "peso_unitario"]) != esperadas:
                avisos.append(f"{clave} ({m.get('ref', 's/ref')}): unidad {unidad} espera {esperadas} dimensiones y trae {dims}.")
            valor = d(m.get("piezas", 1))
            for k in dims:
                valor *= d(m[k])
            if m.get("descontar"):
                valor = -valor
            total += valor
            renglones.append({"clave": clave, "ref": m.get("ref", ""), **{k: m.get(k, "") for k in DIMENSIONES},
                              "piezas": m.get("piezas", 1), "descontar": "sí" if m.get("descontar") else "",
                              "parcial": float(valor)})
        cantidad = float(total.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
        if cantidad <= 0:
            errores.append(f"{clave}: la cantidad sale {cantidad}. Revisa los descuentos.")
        if c.get("confianza") not in ("alta", "media", "baja"):
            avisos.append(f"{clave}: falta 'confianza' (alta, media o baja); se marca como baja.")
            c["confianza"] = "baja"
        conceptos.append({"tipo": "concepto", "clave": clave, "partida": c.get("partida"),
                          "descripcion": c.get("descripcion", ""), "unidad": c.get("unidad", ""),
                          "cantidad": cantidad, "origen": c.get("origen", ""), "confianza": c["confianza"]})
    return conceptos, renglones, avisos, errores


CONCURSO = "Catálogo del concurso"


def cotejar_concurso(presupuesto, conceptos, tolerancia):
    """Con catálogo del concurso, las cantidades de la dependencia no se tocan:
    se anotan las de planos y se listan las diferencias para la junta de aclaraciones."""
    existentes = {f["clave"]: f for f in presupuesto.get("catalogo", [])}
    dudas = []
    for c in conceptos:
        previo = existentes.get(c["clave"])
        if previo is None:
            presupuesto.setdefault("fuera_de_catalogo", []).append({k: v for k, v in c.items() if k != "partida"})
            dudas.append(f"{c['clave']} ({c['descripcion'][:60]}): aparece en planos ({c['cantidad']:,.3f} {c['unidad']}) "
                         "pero no está en el catálogo del concurso.")
            continue
        previo["cantidad_planos"] = c["cantidad"]
        previo["origen_planos"] = c["origen"]
        previo["confianza_planos"] = c["confianza"]
        base = previo.get("cantidad") or 0
        if base == 0:
            dudas.append(f"{c['clave']}: el catálogo trae 0 y en planos salen {c['cantidad']:,.3f} {c['unidad']}.")
            continue
        dif = (c["cantidad"] - base) / base
        if abs(dif) > tolerancia:
            dudas.append(f"{c['clave']} ({previo.get('descripcion', '')[:60]}): catálogo {base:,.3f} vs planos "
                         f"{c['cantidad']:,.3f} {previo.get('unidad', '')} ({dif:+.1%}). Origen: {c['origen']}.")
    presupuesto["dudas_junta_aclaraciones"] = dudas
    return presupuesto, dudas


def fusionar(presupuesto, partidas, conceptos):
    existentes = {f["clave"]: f for f in presupuesto.get("catalogo", [])}
    for c in conceptos:
        if c["clave"] in existentes:
            previo = existentes[c["clave"]]
            for k in ("cantidad", "origen", "confianza", "unidad", "descripcion"):
                if c.get(k) not in (None, ""):
                    previo[k] = c[k]
        else:
            existentes[c["clave"]] = {k: v for k, v in c.items() if k != "partida"}
            existentes[c["clave"]]["matriz"] = []
    orden = []
    usados = set()
    for p in partidas:
        orden.append(existentes.get(p["clave"], {"tipo": "agrupador", **p}))
        usados.add(p["clave"])
        for c in conceptos:
            if c.get("partida") == p["clave"]:
                orden.append(existentes[c["clave"]])
                usados.add(c["clave"])
    for f in presupuesto.get("catalogo", []):
        if f["clave"] not in usados:
            orden.append(f)
            usados.add(f["clave"])
    for c in conceptos:
        if c["clave"] not in usados:
            orden.append(existentes[c["clave"]])
    presupuesto["catalogo"] = orden
    return presupuesto


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("generadores")
    ap.add_argument("--presupuesto", help="presupuesto.json a crear o actualizar")
    ap.add_argument("--tolerancia", type=float, default=0.05,
                    help="con catálogo del concurso: diferencia que se reporta como duda (0.05 = 5 %%)")
    args = ap.parse_args()

    ruta = Path(args.generadores)
    gen = json.loads(ruta.read_text(encoding="utf-8"))
    conceptos, renglones, avisos, errores = calcular(gen)
    if errores:
        print("ERRORES (no se escribió nada):")
        for e in errores:
            print("  -", e)
        sys.exit(1)

    csv_ruta = ruta.with_name(ruta.stem + "_generadores.csv")
    campos = ["clave", "ref", *DIMENSIONES, "piezas", "descontar", "parcial"]
    with open(csv_ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(renglones)
    print(f"Escrito: {csv_ruta}")

    pres_ruta = Path(args.presupuesto) if args.presupuesto else ruta.with_name("presupuesto.json")
    if pres_ruta.exists():
        presupuesto = json.loads(pres_ruta.read_text(encoding="utf-8"))
    else:
        presupuesto = {"obra": gen.get("obra", {}), "factores": {}, "insumos": [], "catalogo": []}
    dudas = None
    if any(f.get("origen") == CONCURSO for f in presupuesto.get("catalogo", [])):
        presupuesto, dudas = cotejar_concurso(presupuesto, conceptos, args.tolerancia)
    else:
        presupuesto = fusionar(presupuesto, gen.get("partidas", []), conceptos)
    pres_ruta.write_text(json.dumps(presupuesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Escrito: {pres_ruta}")

    for c in conceptos:
        marca = "  ← REVISAR" if c["confianza"] == "baja" else ""
        print(f"  {c['clave']:<10} {c['cantidad']:>12,.3f} {c['unidad']:<5} confianza {c['confianza']}{marca}")
    if dudas is not None:
        print("\nCatálogo del concurso: las cantidades de la dependencia se respetan.")
        if dudas:
            print(f"DUDAS PARA LA JUNTA DE ACLARACIONES ({len(dudas)}):")
            for x in dudas:
                print("  -", x)
        else:
            print("Las cantidades de planos coinciden con el catálogo.")
    if avisos:
        print(f"\nAVISOS ({len(avisos)}):")
        for a in avisos:
            print("  -", a)


if __name__ == "__main__":
    main()
