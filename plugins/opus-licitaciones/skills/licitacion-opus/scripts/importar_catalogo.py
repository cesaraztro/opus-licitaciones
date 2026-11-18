#!/usr/bin/env python3
"""Lee el catálogo de conceptos del concurso (Excel o CSV de la dependencia) y lo pasa a presupuesto.json.

Uso:
    python importar_catalogo.py catalogo_concurso.xlsx --presupuesto presupuesto.json
           [--hoja "Catálogo"] [--columnas "clave=A,descripcion=B,unidad=C,cantidad=D"]

- Encuentra sola la fila de encabezados (aunque el archivo traiga membrete arriba).
- Filas con clave y descripción pero sin unidad ni cantidad = partidas (agrupadores).
  El nivel sale de la clave: "1" → 1, "1.2" → 2, "1.2.3" → 3.
- Filas que solo traen descripción = continuación de la descripción anterior.
- El catálogo del concurso manda: claves, descripciones, unidades y cantidades se
  toman tal cual. Las matrices que ya existan en presupuesto.json se conservan.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from opus_tabla import numero, tabla, utf8_en_consola  # noqa: E402

ORIGEN = "Catálogo del concurso"


def nivel_de(clave):
    partes = [p for p in re.split(r"[.\-]", str(clave)) if p]
    return max(1, len(partes))


def main():
    utf8_en_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("catalogo")
    ap.add_argument("--presupuesto", default="presupuesto.json")
    ap.add_argument("--hoja")
    ap.add_argument("--columnas", help='mapeo manual, p. ej. "clave=A,descripcion=B,unidad=C,cantidad=D"')
    ap.add_argument("--fila-encabezado", type=int, help="con --columnas: número de fila del encabezado (base 1)")
    args = ap.parse_args()

    filas, mapa = tabla(args.catalogo, ("clave", "descripcion", "unidad", "cantidad"),
                        ("clave", "descripcion", "unidad", "cantidad"),
                        hoja=args.hoja, columnas=args.columnas, fila_encabezado=args.fila_encabezado)

    catalogo, avisos = [], []
    for f in filas:
        clave = str(f.get("clave") or "").strip()
        desc = " ".join(str(f.get("descripcion") or "").split())
        unidad = str(f.get("unidad") or "").strip()
        cantidad = numero(f.get("cantidad"))
        if not clave and desc and catalogo:
            catalogo[-1]["descripcion"] += " " + desc
            continue
        if not clave:
            continue
        if not unidad and cantidad is None:
            catalogo.append({"tipo": "agrupador", "nivel": nivel_de(clave), "clave": clave, "descripcion": desc})
            continue
        if cantidad is None:
            avisos.append(f"{clave}: sin cantidad en el catálogo; se deja en 0 para que la saquen los planos.")
            cantidad = 0.0
        if not unidad:
            avisos.append(f"{clave}: sin unidad en el catálogo.")
        catalogo.append({"tipo": "concepto", "clave": clave, "descripcion": desc, "unidad": unidad,
                         "cantidad": cantidad, "origen": ORIGEN, "confianza": "alta"})

    claves = [c["clave"] for c in catalogo]
    repetidas = sorted({c for c in claves if claves.count(c) > 1})
    if repetidas:
        sys.exit(f"El catálogo trae claves repetidas: {repetidas}. Revísalo antes de importar.")

    ruta = Path(args.presupuesto)
    if ruta.exists():
        presupuesto = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        presupuesto = {"obra": {}, "factores": {}, "insumos": [], "catalogo": []}
    previos = {f["clave"]: f for f in presupuesto.get("catalogo", [])}
    for c in catalogo:
        if c["tipo"] == "concepto" and c["clave"] in previos:
            c["matriz"] = previos[c["clave"]].get("matriz", [])
        elif c["tipo"] == "concepto":
            c["matriz"] = []
    fuera = [k for k, f in previos.items() if f.get("tipo") == "concepto" and k not in set(claves)]
    if fuera:
        presupuesto["fuera_de_catalogo"] = [previos[k] for k in fuera]
        avisos.append(f"{len(fuera)} conceptos que ya tenías no vienen en el catálogo del concurso: {fuera}. "
                      "Se movieron a 'fuera_de_catalogo'.")
    presupuesto["catalogo"] = catalogo
    ruta.write_text(json.dumps(presupuesto, ensure_ascii=False, indent=2), encoding="utf-8")

    letras = {c: chr(65 + j) if j < 26 else str(j + 1) for c, j in mapa.items()}
    n_con = sum(1 for c in catalogo if c["tipo"] == "concepto")
    n_agr = len(catalogo) - n_con
    print(f"Columnas usadas: {letras}")
    print(f"Partidas: {n_agr}   Conceptos: {n_con}")
    print(f"Escrito: {ruta}")
    if avisos:
        print(f"\nAVISOS ({len(avisos)}):")
        for a in avisos:
            print("  -", a)


if __name__ == "__main__":
    main()
