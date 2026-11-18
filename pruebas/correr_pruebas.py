#!/usr/bin/env python3
"""Pruebas del plugin con una obra ficticia: catálogo del concurso, planos, generadores,\nbase histórica, precios unitarios, Excel para Liga Office y verificación.

Uso:  python pruebas/correr_pruebas.py
No toca los archivos de muestra: trabaja en una carpeta temporal.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)

RAIZ = Path(__file__).resolve().parent.parent
PRUEBAS = RAIZ / "pruebas"
PLUGIN = RAIZ / "plugins/opus-licitaciones"
SK = PLUGIN / "skills"
GEN = SK / "lectura-planos/scripts/generadores.py"
PLANOS = SK / "lectura-planos/scripts/preparar_planos.py"
PU = SK / "opus-precios-unitarios/scripts/calcular_pu.py"
REF = SK / "opus-precios-unitarios/scripts/buscar_referencias.py"
IDX = SK / "opus-precios-unitarios/scripts/indexar_historico.py"
CON = SK / "opus-precios-unitarios/scripts/consultar_precios.py"
LIGA = SK / "opus-liga-excel/scripts/generar_liga.py"
VER = SK / "opus-liga-excel/scripts/verificar_liga.py"
CAT = SK / "licitacion-opus/scripts/importar_catalogo.py"
sys.path.insert(0, str(PLUGIN / "lib"))

fallas = []


def correr(*args, espera=0):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != espera:
        fallas.append(f"{Path(args[0]).name} salió con {r.returncode} (esperaba {espera}):\n{r.stdout}{r.stderr}")
    return r.stdout


def checar(condicion, mensaje):
    print(("  ok   " if condicion else "  FALLA ") + mensaje)
    if not condicion:
        fallas.append(mensaje)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    shutil.copy(PRUEBAS / "presupuesto_base.json", tmp / "presupuesto.json")
    shutil.copy(PRUEBAS / "generadores_muestra.json", tmp / "generadores.json")

    print("1. Generadores (lectura de planos)")
    out = correr(GEN, tmp / "generadores.json", "--presupuesto", tmp / "presupuesto.json")
    p = json.loads((tmp / "presupuesto.json").read_text(encoding="utf-8"))
    cat = {f["clave"]: f for f in p["catalogo"]}
    checar(cat["A-01"]["cantidad"] == 75.0, "A-01 = 50 × 1.5 = 75 m2")
    checar(cat["B-01"]["cantidad"] == 74.28, "B-01 = 75 − 2 registros de 0.6 × 0.6 = 74.28 m2")
    checar(cat["B-02"]["cantidad"] == 50.0, "B-02 = 50 ml")
    checar(len(cat["B-01"]["matriz"]) == 4, "las matrices existentes se conservan al actualizar cantidades")
    checar([f["clave"] for f in p["catalogo"]] == ["A", "A-01", "B", "B-01", "B-02"], "orden de partidas y conceptos")
    checar("REVISAR" in out, "B-02 con confianza baja sale marcado para revisar")
    checar((tmp / "generadores_generadores.csv").exists(), "hoja de números generadores en CSV")

    print("2. Precios unitarios")
    out = correr(PU, tmp / "presupuesto.json")
    p = json.loads((tmp / "presupuesto_calculado.json").read_text(encoding="utf-8"))
    cat = {f["clave"]: f for f in p["catalogo"]}
    # B-01 a mano: CD = 0.105×2850 + 0.05×1450 + 3%×72.50 + 0.02×85 = 375.625
    # PU = 375.625 × 1.14 × 1.012 × 1.10 × 1.005 = 479.0696 → 479.07
    checar(cat["B-01"]["costo_directo"] == 375.63, f"B-01 costo directo 375.63 (sale {cat['B-01']['costo_directo']})")
    checar(cat["B-01"]["precio_unitario"] == 479.07, f"B-01 PU 479.07 (sale {cat['B-01']['precio_unitario']})")
    checar(cat["B-01"]["importe"] == 35585.32, f"B-01 importe 479.07 × 74.28 = 35,585.32 (sale {cat['B-01']['importe']})")
    checar(cat["B-01"]["desglose"]["herramienta"] == 2.18, "herramienta menor = 3 % de la mano de obra")
    total = round(sum(f["importe"] for f in p["catalogo"] if f["tipo"] == "concepto"), 2)
    checar(p["resumen"]["total_sin_iva"] == total, f"total = suma de importes ({total:,.2f})")
    checar(any("MAT-CAL" in a for a in p["resumen"]["avisos"]), "insumo sin obra de referencia queda en avisos")
    checar(not any("HE-MENOR" in a and "sin costo" in a for a in p["resumen"]["avisos"]), "herramienta menor (%mo) no pide costo")

    print("3. Errores que deben detener el cálculo")
    malo = json.loads((tmp / "presupuesto.json").read_text(encoding="utf-8"))
    malo["catalogo"][1]["matriz"].append({"insumo": "NO-EXISTE", "cantidad": 1})
    (tmp / "malo.json").write_text(json.dumps(malo), encoding="utf-8")
    out = correr(PU, tmp / "malo.json", espera=1)
    checar("NO-EXISTE" in out and not (tmp / "malo_calculado.json").exists(), "insumo inexistente detiene el cálculo sin escribir")

    print("4. Excel para Liga Office")
    correr(LIGA, tmp / "presupuesto_calculado.json")
    xlsx = tmp / "presupuesto_liga.xlsx"
    checar(xlsx.exists(), "se genera presupuesto_liga.xlsx")
    out = correr(VER, xlsx, tmp / "presupuesto_calculado.json")
    checar(out.startswith("OK"), "el verificador acepta el Excel")

    print("5. El verificador detecta un Excel dañado")
    from openpyxl import load_workbook
    wb = load_workbook(xlsx)
    wb["Catalogo"]["E3"] = None      # borra la cantidad de A-01 (fila 3)
    wb["Matrices"]["C2"] = "FANTASMA"  # insumo que no existe
    wb.save(tmp / "danado.xlsx")
    out = correr(VER, tmp / "danado.xlsx", tmp / "presupuesto_calculado.json", espera=1)
    checar("'cantidad' vacío" in out, "detecta cantidad vacía")
    checar("FANTASMA" in out, "detecta insumo de matriz que no existe")

    print("6. Búsqueda en la bóveda")
    boveda = tmp / "boveda"
    (boveda / "Obras").mkdir(parents=True)
    (boveda / "Obras/Puente Río Sonora 2025.md").write_text(
        "# Puente\n- Concreto premezclado f'c=250 bombeable: $3,120.00 m3\n- Acero de refuerzo fy=4200: $24,800 ton\n",
        encoding="utf-8")
    (boveda / "Obras/Bodega 2024.md").write_text("Concreto hecho en obra f'c=150\n", encoding="utf-8")
    out = correr(REF, boveda, "concreto", "f'c=250")
    checar(out.splitlines()[0].startswith("[[Obras/Puente Río Sonora 2025]]"), "la obra con más coincidencias sale primero")
    checar("$3,120.00" in out, "muestra el precio encontrado en la línea")

    print("7. Catálogo del concurso (Excel de la dependencia con membrete)")
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    for fila in [["GOBIERNO DEL ESTADO DE SONORA"], ["Licitación pública LO-PRUEBA-001"], [],
                 ["Catálogo de conceptos"], [],
                 ["CLAVE", "DESCRIPCIÓN DEL CONCEPTO", "UNIDAD", "CANTIDAD", "P.U.", "IMPORTE"],
                 ["1", "PRELIMINARES"],
                 ["1.1", "Trazo y nivelación del terreno con equipo topográfico.", "M2", 75],
                 ["2", "BANQUETAS Y GUARNICIONES"],
                 ["2.1", "Banqueta de concreto f'c=200 kg/cm2 de 10 cm", "M2", "74.28"],
                 [None, "de espesor, acabado escobillado."],
                 ["2.2", "Guarnición de concreto f'c=200 kg/cm2 sección trapezoidal.", "ML", "45.00"]]:
        ws.append(fila)
    wb.save(tmp / "catalogo_concurso.xlsx")
    base = json.loads((PRUEBAS / "presupuesto_base.json").read_text(encoding="utf-8"))
    base["catalogo"] = []
    (tmp / "concurso.json").write_text(json.dumps(base), encoding="utf-8")
    out = correr(CAT, tmp / "catalogo_concurso.xlsx", "--presupuesto", tmp / "concurso.json")
    pc = json.loads((tmp / "concurso.json").read_text(encoding="utf-8"))
    cc = {f["clave"]: f for f in pc["catalogo"]}
    checar("Partidas: 2   Conceptos: 3" in out, "encuentra encabezados debajo del membrete: 2 partidas, 3 conceptos")
    checar(cc["2"]["tipo"] == "agrupador" and cc["2"]["nivel"] == 1, "fila sin unidad ni cantidad = partida de nivel 1")
    checar(cc["2.1"]["descripcion"].endswith("acabado escobillado."), "une la descripción partida en dos filas")
    checar(cc["2.1"]["cantidad"] == 74.28 and cc["2.2"]["cantidad"] == 45.0, "lee cantidades escritas como texto")

    print("8. Planos contra catálogo del concurso (dudas para la junta)")
    gen = json.loads((PRUEBAS / "generadores_muestra.json").read_text(encoding="utf-8"))
    claves = {"A-01": "1.1", "B-01": "2.1", "B-02": "2.2"}
    for c in gen["conceptos"]:
        c["clave"] = claves[c["clave"]]
    (tmp / "gen_concurso.json").write_text(json.dumps(gen), encoding="utf-8")
    out = correr(GEN, tmp / "gen_concurso.json", "--presupuesto", tmp / "concurso.json")
    pc = json.loads((tmp / "concurso.json").read_text(encoding="utf-8"))
    cc = {f["clave"]: f for f in pc["catalogo"]}
    checar(cc["2.2"]["cantidad"] == 45.0 and cc["2.2"]["cantidad_planos"] == 50.0,
           "respeta la cantidad de la dependencia (45) y guarda la de planos (50)")
    dudas = pc["dudas_junta_aclaraciones"]
    checar(len(dudas) == 1 and "2.2" in dudas[0] and "+11.1%" in dudas[0], "solo 2.2 sale como duda (+11.1 %)")

    print("9. Preparar planos PDF")
    import fitz
    doc = fitz.open()
    hoja = doc.new_page(width=842, height=595)
    hoja.insert_text((60, 60), "PLANO A-01  PLANTA GENERAL", fontsize=14)
    hoja.insert_text((60, 90), "ESC. 1:100", fontsize=10)
    hoja.insert_text((300, 300), "12.40", fontsize=8)
    hoja.insert_text((500, 300), "3.50", fontsize=8)
    hoja.draw_line((100, 320), (700, 320))
    escaneada = doc.new_page(width=842, height=595)
    escaneada.draw_rect(fitz.Rect(100, 100, 400, 300))
    doc.save(tmp / "planos.pdf")
    correr(PLANOS, tmp / "planos.pdf", "--salida", tmp / "prep", "--dpi", "40", "--dpi-cuadros", "60")
    indice = json.loads((tmp / "prep/planos/indice.json").read_text(encoding="utf-8"))
    h1, h2 = indice["hojas"]
    checar(h1["clave_plano"] == "A-01" and h1["escalas"] == ["1:100"], "detecta clave del plano y escala")
    checar(h1["cotas_encontradas"] >= 2 and "12.40" in h1["muestra_cotas"], "extrae las cotas del texto vectorial")
    checar(len(h1["cuadros"]) == 6 and all((tmp / "prep/planos" / c["archivo"]).exists() for c in h1["cuadros"]),
           "genera 6 acercamientos (3x2)")
    checar(h2["escaneado"] and not h1["escaneado"], "marca como escaneada la hoja sin texto")

    print("10. Base histórica de precios")
    wb = Workbook(); ws = wb.active
    for fila in [["CONSTRUCTORA DE PRUEBA"], ["Listado de insumos"], [],
                 ["Clave", "Descripción", "Unidad", "Tipo", "Costo"],
                 ["MAT-CONC-200", "Concreto premezclado f'c=200 kg/cm2", "m3", "Material", "$2,600.00"],
                 ["MO-CUA-ALB", "Cuadrilla 1 albañil + 1 peón", "jor", "Mano de obra", 1300]]:
        ws.append(fila)
    wb.save(tmp / "insumos_2025.xlsx")
    (tmp / "insumos_2026.csv").write_text("Clave,Descripción,Unidad,Costo\nMAT-CONC-200,Concreto f'c=200,m3,2700\n",
                                          encoding="utf-8")
    hist = tmp / "historico.csv"
    correr(IDX, tmp / "insumos_2025.xlsx", "--obra", "Obra 2025", "--fecha", "2025-01", "--historico", hist)
    correr(IDX, tmp / "insumos_2026.csv", "--obra", "Obra 2026", "--fecha", "2026-01", "--historico", hist)
    out = correr(IDX, tmp / "insumos_2025.xlsx", "--obra", "Obra 2025", "--fecha", "2025-01", "--historico", hist)
    import historico
    filas = historico.cargar(hist)
    checar(len(filas) == 3, "reindexar la misma obra la reemplaza, no la duplica")
    checar({f["tipo"] for f in filas if f["obra"] == "Obra 2025"} == {"material", "mano_obra"}, "traduce el tipo de Opus")
    out = correr(CON, "concreto", "200", "--historico", hist, "--unidad", "m3")
    checar("mediana 2,650.00" in out, "consulta: mediana de 2,600 y 2,700 = 2,650")
    from datetime import date
    checar(abs(historico.escalar(100, "2025-11-18", 0.10, hoy=date(2026, 11, 18)) - 110) < 0.05, "escalación 10 % anual")
    out = correr(PU, tmp / "presupuesto.json", "--historico", hist, "--desviacion", "0.05")
    checar("MAT-CONC-200" in out and "+8% contra la mediana" in out, "avisa: concreto a 2,850 vs mediana 2,650 (+8 %)")
    checar("MO-CUA-ALB" in out and "+12% contra la mediana" in out, "avisa: cuadrilla a 1,450 vs 1,300 (+12 %)")
    correr(IDX, tmp / "presupuesto_calculado.json", "--historico", hist)
    checar(any(f["obra"] == "Banqueta y guarnición calle de prueba" for f in historico.cargar(hist)),
           "un presupuesto terminado alimenta la base histórica")

print()
if fallas:
    print(f"FALLARON {len(fallas)}:")
    for f in fallas:
        print(" -", f)
    sys.exit(1)
print("Todas las pruebas pasaron.")
