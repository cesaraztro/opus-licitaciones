#!/usr/bin/env python3
"""Calcula precios unitarios de un presupuesto.json (ver ESQUEMA.md).

Uso:
    python calcular_pu.py presupuesto.json [--salida presupuesto_calculado.json]
           [--historico historico_precios.csv] [--desviacion 0.25] [--escalacion 0.05]

Con --historico compara el costo de cada insumo contra la mediana de obras anteriores
(escalada a hoy si das --escalacion) y avisa cuando se aleja más de --desviacion.

Escribe:
    <base>_calculado.json  el mismo presupuesto con costo directo, desglose, PU e importe
    <base>_pu.csv          tabla de precios unitarios para revisar en Excel
Sale con código 1 si hay errores que impiden calcular (insumo inexistente,
clave duplicada, factores faltantes). Los avisos no detienen el cálculo.
"""
import argparse
import csv
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

TIPOS = ("material", "mano_obra", "herramienta", "equipo", "flete")
FACTORES_OBLIGATORIOS = ("financiamiento", "utilidad", "cargos_adicionales")
DOS = Decimal("0.01")
SEIS = Decimal("0.000001")


def d(valor):
    return Decimal(str(valor))


def redondear(valor, paso=DOS):
    return valor.quantize(paso, rounding=ROUND_HALF_UP)


def leer_factores(factores, errores):
    for clave in FACTORES_OBLIGATORIOS:
        if clave not in factores:
            errores.append(f"Falta el factor '{clave}' en 'factores'.")
    if "indirectos" in factores:
        indirectos = d(factores["indirectos"])
    elif "indirectos_campo" in factores or "indirectos_oficina" in factores:
        indirectos = d(factores.get("indirectos_campo", 0)) + d(factores.get("indirectos_oficina", 0))
    else:
        errores.append("Faltan los indirectos: usa 'indirectos' o 'indirectos_campo' + 'indirectos_oficina'.")
        indirectos = Decimal(0)
    return {
        "indirectos": indirectos,
        "financiamiento": d(factores.get("financiamiento", 0)),
        "utilidad": d(factores.get("utilidad", 0)),
        "cargos_adicionales": d(factores.get("cargos_adicionales", 0)),
    }


def calcular(presupuesto):
    errores, avisos = [], []
    f = leer_factores(presupuesto.get("factores", {}), errores)

    insumos = {}
    for ins in presupuesto.get("insumos", []):
        clave = ins.get("clave")
        if not clave:
            errores.append(f"Insumo sin clave: {ins}")
            continue
        if clave in insumos:
            errores.append(f"Insumo duplicado: {clave}")
        if ins.get("tipo") not in TIPOS:
            errores.append(f"Insumo {clave}: tipo '{ins.get('tipo')}' no válido ({', '.join(TIPOS)}).")
        es_porcentual = str(ins.get("unidad", "")).lower().replace(" ", "") in ("%mo", "%")
        if not ins.get("costo") and not es_porcentual:
            avisos.append(f"Insumo {clave} sin costo: el concepto que lo use saldrá bajo.")
        if not ins.get("fuente"):
            avisos.append(f"Insumo {clave} sin obra de referencia (fuente): confirmar el costo con el usuario.")
        insumos[clave] = ins

    vistos = set()
    total = Decimal(0)
    for fila in presupuesto.get("catalogo", []):
        clave = fila.get("clave")
        if clave in vistos:
            errores.append(f"Clave duplicada en el catálogo: {clave}")
        vistos.add(clave)
        if fila.get("tipo") == "agrupador":
            if not isinstance(fila.get("nivel"), int) or fila["nivel"] < 1:
                errores.append(f"Agrupador {clave} sin 'nivel' válido (1, 2, 3…).")
            continue
        if fila.get("tipo") != "concepto":
            errores.append(f"Fila {clave}: 'tipo' debe ser 'agrupador' o 'concepto'.")
            continue
        if fila.get("cantidad") in (None, ""):
            errores.append(f"Concepto {clave} sin cantidad.")
            continue
        if fila.get("confianza") == "baja":
            avisos.append(f"Concepto {clave}: cantidad con confianza baja ({fila.get('origen', 'sin origen')}).")
        matriz = fila.get("matriz") or []
        if not matriz:
            avisos.append(f"Concepto {clave} sin matriz: PU en cero.")

        desglose = {t: Decimal(0) for t in TIPOS}
        porcentuales = []
        for item in matriz:
            ins = insumos.get(item.get("insumo"))
            if ins is None:
                errores.append(f"Concepto {clave}: el insumo '{item.get('insumo')}' no existe en 'insumos'.")
                continue
            if "porcentaje_mo" in item:
                porcentuales.append((ins, d(item["porcentaje_mo"])))
                continue
            importe = d(item.get("cantidad", 0)) * d(ins.get("costo") or 0)
            item["importe"] = float(redondear(importe, SEIS))
            desglose[ins["tipo"]] += importe
        mano_obra = desglose["mano_obra"]
        for ins, pct in porcentuales:
            importe = mano_obra * pct
            desglose[ins["tipo"]] += importe
            for item in matriz:
                if item.get("insumo") == ins["clave"] and "porcentaje_mo" in item:
                    item["importe"] = float(redondear(importe, SEIS))

        cd = sum(desglose.values(), Decimal(0))
        ci = cd * f["indirectos"]
        cf = (cd + ci) * f["financiamiento"]
        cu = (cd + ci + cf) * f["utilidad"]
        ca = (cd + ci + cf + cu) * f["cargos_adicionales"]
        pu = redondear(cd + ci + cf + cu + ca)
        importe = redondear(pu * d(fila["cantidad"]))
        total += importe

        fila["desglose"] = {t: float(redondear(v)) for t, v in desglose.items()}
        fila["costo_directo"] = float(redondear(cd))
        fila["sobrecosto"] = {
            "indirectos": float(redondear(ci)),
            "financiamiento": float(redondear(cf)),
            "utilidad": float(redondear(cu)),
            "cargos_adicionales": float(redondear(ca)),
        }
        fila["precio_unitario"] = float(pu)
        fila["importe"] = float(importe)

    presupuesto["resumen"] = {
        "total_sin_iva": float(redondear(total)),
        "conceptos": sum(1 for x in presupuesto.get("catalogo", []) if x.get("tipo") == "concepto"),
        "avisos": avisos,
    }
    return presupuesto, errores, avisos


def revisar_historico(presupuesto, ruta, desviacion, tasa):
    """Avisos de costos fuera de rango contra la base histórica."""
    import historico
    base = historico.cargar(ruta)
    avisos = []
    if not base:
        return [f"Base histórica vacía o inexistente ({ruta}): no se revisaron costos."]
    for ins in presupuesto.get("insumos", []):
        grupo, por = historico.similares(base, ins.get("clave"), ins.get("descripcion"), ins.get("unidad"))
        if not grupo:
            continue
        ref = historico.referencia(grupo, tasa)
        ins["historico"] = {"mediana": round(ref["mediana"], 2), "n": ref["n"], "obras": ref["obras"], "por": por}
        if not ins.get("costo"):
            avisos.append(f"Insumo {ins['clave']} sin costo: la base histórica sugiere ${ref['mediana']:,.2f} "
                          f"({ref['n']} precios, {', '.join(ref['obras'][:3])}).")
            continue
        dif = ins["costo"] / ref["mediana"] - 1
        if abs(dif) > desviacion:
            avisos.append(f"Insumo {ins['clave']} a ${ins['costo']:,.2f} está {dif:+.0%} contra la mediana histórica "
                          f"${ref['mediana']:,.2f} ({ref['n']} precios; rango ${ref['minimo']:,.2f}–${ref['maximo']:,.2f}).")
    return avisos


def escribir_csv(presupuesto, ruta):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Clave", "Descripción", "Unidad", "Cantidad", *[t.replace("_", " ").title() for t in TIPOS],
                    "Costo directo", "Precio unitario", "Importe", "Confianza", "Origen"])
        for fila in presupuesto["catalogo"]:
            if fila.get("tipo") == "agrupador":
                w.writerow([fila["clave"], fila["descripcion"]])
                continue
            if "precio_unitario" not in fila:
                continue
            w.writerow([fila["clave"], fila["descripcion"], fila["unidad"], fila["cantidad"],
                        *[fila["desglose"][t] for t in TIPOS], fila["costo_directo"],
                        fila["precio_unitario"], fila["importe"], fila.get("confianza", ""), fila.get("origen", "")])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada")
    p.add_argument("--salida")
    p.add_argument("--historico", help="historico_precios.csv para revisar costos")
    p.add_argument("--desviacion", type=float, default=0.25, help="0.25 = avisar si se aleja más de 25 %%")
    p.add_argument("--escalacion", type=float, default=0.0, help="tasa anual para llevar precios históricos a hoy")
    args = p.parse_args()

    entrada = Path(args.entrada)
    presupuesto = json.loads(entrada.read_text(encoding="utf-8"))
    presupuesto, errores, avisos = calcular(presupuesto)
    if args.historico and not errores:
        extra = revisar_historico(presupuesto, args.historico, args.desviacion, args.escalacion)
        avisos.extend(extra)
        presupuesto["resumen"]["avisos"] = avisos

    if errores:
        print("ERRORES (no se escribió nada):")
        for e in errores:
            print("  -", e)
        sys.exit(1)

    base = entrada.with_suffix("")
    if base.name.endswith("_calculado"):
        base = base.with_name(base.name[: -len("_calculado")])
    salida = Path(args.salida) if args.salida else base.with_name(base.name + "_calculado.json")
    salida.write_text(json.dumps(presupuesto, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_ruta = base.with_name(base.name + "_pu.csv")
    escribir_csv(presupuesto, csv_ruta)

    print(f"Conceptos: {presupuesto['resumen']['conceptos']}")
    print(f"Total sin IVA: ${presupuesto['resumen']['total_sin_iva']:,.2f}")
    print(f"Escrito: {salida}")
    print(f"Escrito: {csv_ruta}")
    if avisos:
        print(f"\nAVISOS ({len(avisos)}):")
        for a in avisos:
            print("  -", a)


if __name__ == "__main__":
    main()
