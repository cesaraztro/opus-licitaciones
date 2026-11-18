#!/usr/bin/env python3
"""Prepara planos PDF para leerlos sin perder detalle.

Uso:
    python preparar_planos.py planos.pdf [otro.pdf ...] [--salida planos_preparados]
           [--dpi 110] [--dpi-cuadros 220] [--cuadricula 3x2]

Por cada hoja genera:
    hoja-01.png               vista completa (para ubicar ejes, cortes y cuadro de datos)
    hoja-01_c1-1.png ...      acercamientos en cuadrícula con 10 % de traslape (para leer cotas)
    hoja-01_texto.json        todo el texto vectorial con su posición: cotas, ejes, notas
Y un indice.json con, por hoja: clave del plano, escala, cotas encontradas y si es
escaneado (sin texto: solo se puede leer de la imagen).

Las cotas del texto vectorial son exactas: úsalas antes que leerlas de la imagen.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("Falta PyMuPDF. Instálalo con:  python -m pip install pymupdf")

ESCALA = re.compile(r"\bESC(?:ALA)?\.?\s*:?\s*(1\s*:\s*[\d,]+)", re.I)
CLAVE_PLANO = re.compile(r"\b((?:A|ARQ|E|EST|IE|IH|IS|IEL|ISA|TOP|URB|PAV|CIM|DET|INS|P|S)-?\d{1,3}[A-Z]?)\b")
COTA = re.compile(r"^\d{1,4}(?:[.,]\d{1,3})?(?:m|cm|mm)?$", re.I)


def preparar(pdf, salida, dpi, dpi_cuadros, cols, filas):
    doc = fitz.open(pdf)
    carpeta = salida / Path(pdf).stem
    carpeta.mkdir(parents=True, exist_ok=True)
    hojas = []
    for n, page in enumerate(doc, 1):
        base = f"hoja-{n:02d}"
        page.get_pixmap(dpi=dpi).save(carpeta / f"{base}.png")

        r = page.rect
        w, h = r.width / cols, r.height / filas
        mx, my = w * 0.10, h * 0.10
        cuadros = []
        for i in range(filas):
            for j in range(cols):
                clip = fitz.Rect(max(r.x0, r.x0 + j * w - mx), max(r.y0, r.y0 + i * h - my),
                                 min(r.x1, r.x0 + (j + 1) * w + mx), min(r.y1, r.y0 + (i + 1) * h + my))
                nombre = f"{base}_c{i + 1}-{j + 1}.png"
                page.get_pixmap(dpi=dpi_cuadros, clip=clip).save(carpeta / nombre)
                cuadros.append({"archivo": nombre, "fila": i + 1, "columna": j + 1,
                                "zona": [round(clip.x0), round(clip.y0), round(clip.x1), round(clip.y1)]})

        palabras = page.get_text("words")
        texto = [{"t": p[4], "x": round(p[0], 1), "y": round(p[1], 1)} for p in palabras]
        (carpeta / f"{base}_texto.json").write_text(json.dumps(texto, ensure_ascii=False), encoding="utf-8")
        plano = page.get_text()
        escalas = sorted({re.sub(r"\s", "", m) for m in ESCALA.findall(plano)})
        claves = [m for m in CLAVE_PLANO.findall(plano)]
        cotas = [p["t"] for p in texto if COTA.match(p["t"])]
        hojas.append({
            "hoja": n,
            "imagen": f"{base}.png",
            "cuadros": cuadros,
            "texto": f"{base}_texto.json",
            "clave_plano": max(set(claves), key=claves.count) if claves else None,
            "escalas": escalas,
            "cotas_encontradas": len(cotas),
            "muestra_cotas": cotas[:25],
            "escaneado": len(palabras) == 0,
            "tamano_pt": [round(r.width), round(r.height)],
        })
    indice = {"pdf": str(pdf), "hojas": hojas}
    (carpeta / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")
    return carpeta, hojas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--salida", default="planos_preparados")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--dpi-cuadros", type=int, default=220)
    ap.add_argument("--cuadricula", default="3x2", help="columnas x filas de acercamientos (3x2 por defecto)")
    args = ap.parse_args()
    cols, filas = (int(x) for x in args.cuadricula.lower().split("x"))

    salida = Path(args.salida)
    for pdf in args.pdfs:
        carpeta, hojas = preparar(pdf, salida, args.dpi, args.dpi_cuadros, cols, filas)
        print(f"{pdf} → {carpeta}  ({len(hojas)} hojas)")
        for h in hojas:
            tipo = "ESCANEADO: leer de imagen" if h["escaneado"] else f"{h['cotas_encontradas']} cotas en texto"
            print(f"  Hoja {h['hoja']:>2}  plano {h['clave_plano'] or '¿?':<8} escala {', '.join(h['escalas']) or '¿?':<10} {tipo}")


if __name__ == "__main__":
    main()
