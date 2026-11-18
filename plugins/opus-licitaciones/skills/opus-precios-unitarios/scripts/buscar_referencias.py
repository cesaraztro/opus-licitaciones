#!/usr/bin/env python3
"""Busca en la bóveda de Obsidian del usuario obras de referencia para un concepto o insumo.

Uso:
    python buscar_referencias.py RUTA_BOVEDA "concreto f'c=250" "losa" [--max 8]

Devuelve las notas que más términos contienen, con las líneas que coinciden y
los importes ($) que aparecen en esas líneas. Solo lee; nunca modifica la bóveda.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

DINERO = re.compile(r"\$\s?[\d,]+(?:\.\d+)?")


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("boveda")
    p.add_argument("terminos", nargs="+")
    p.add_argument("--max", type=int, default=8, help="notas a mostrar")
    p.add_argument("--lineas", type=int, default=6, help="líneas por nota")
    args = p.parse_args()

    raiz = Path(args.boveda)
    if not raiz.is_dir():
        sys.exit(f"No existe la bóveda: {raiz}")
    terminos = [normalizar(t) for t in args.terminos]

    resultados = []
    for nota in raiz.rglob("*.md"):
        if any(parte.startswith(".") for parte in nota.relative_to(raiz).parts):
            continue
        try:
            lineas = nota.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        coincidencias, encontrados = [], set()
        for n, linea in enumerate(lineas, 1):
            ln = normalizar(linea)
            hits = [t for t in terminos if t in ln]
            if hits:
                encontrados.update(hits)
                coincidencias.append((len(hits), n, linea.strip()))
        if encontrados:
            coincidencias.sort(key=lambda x: (-x[0], x[1]))
            resultados.append((len(encontrados), len(coincidencias), nota, coincidencias))

    if not resultados:
        print("Sin coincidencias. Prueba con sinónimos o términos más cortos.")
        return
    resultados.sort(key=lambda r: (-r[0], -r[1]))
    for cubiertos, total, nota, coincidencias in resultados[: args.max]:
        enlace = nota.relative_to(raiz).with_suffix("").as_posix()
        print(f"[[{enlace}]]  ({cubiertos}/{len(terminos)} términos, {total} líneas)")
        for _, n, linea in coincidencias[: args.lineas]:
            montos = DINERO.findall(linea)
            extra = f"   ← {', '.join(montos)}" if montos else ""
            print(f"   L{n}: {linea[:160]}{extra}")
        print()


if __name__ == "__main__":
    main()
