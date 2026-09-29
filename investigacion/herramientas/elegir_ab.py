"""Elige las A y B de la entrega que todavía no tienen investigación completa y las reparte para los agentes.

Cubre el hueco que deja elegir_tanda.py: esa herramienta saltea todo lo que figura en un *_out*.csv, incluidas
las salidas de la pasada rápida (q*_out), así que las empresas que la pasada rápida confirmó como B nunca
llegaban al nivel 4 del embudo (decisor, canal, gancho y borrador).

Uso (desde la raíz del repo, después de `python -m prospeccion todo`):
    PYTHONPATH=. python investigacion/herramientas/elegir_ab.py t10 36 3
Deja investigacion/tandas/t10_0.csv ... (sin encabezado, mismo formato que elegir_tanda.py) para
instrucciones_agente.md; después se suman con sumar.py como cualquier tanda t.
"""
import glob
import sys
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

nombre, cantidad, partes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = Path("investigacion/tandas")
e = pd.read_csv("datos/salida/entrega.csv", sep=";", dtype=str).fillna("")
hechas = set(pd.read_csv("canal/respuestas/20260926-prospectos-AB.csv", sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
# Investigaciones completas ya hechas o en curso (tandas t y nueva), con o sin resultado
for f in glob.glob(str(T / "t*_out*.csv")) + glob.glob(str(T / "nueva_out*.csv")):
    hechas |= set(pd.read_csv(f, sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
for f in glob.glob(str(T / "t*_[0-9]*.csv")) + glob.glob(str(T / "nueva0*.csv")):
    if "_out" not in f:
        hechas |= set(pd.read_csv(f, sep=";", dtype=str, header=None)[0].map(nombre_normalizado))
c = e[e["categoria"].isin(["A", "B"]) & ~e["razon_social"].map(nombre_normalizado).isin(hechas)]
c = c.assign(_c=c["categoria"].map({"A": 0, "B": 1}), _p=pd.to_numeric(c["puntaje"], errors="coerce").fillna(0))
c = c.sort_values(["_c", "_p"], ascending=[True, False])
print(f"A/B sin investigación completa: {len(c)} ({c['categoria'].value_counts().to_dict()})")
sel = c.head(cantidad).rename(columns={"dominio_email": "dominio_conocido", "rubro_coi": "rubro_supuesto"})[
    ["razon_social", "localidad", "provincia", "dominio_conocido", "rubro_supuesto"]]
for i in range(partes):
    sel.iloc[i::partes].to_csv(T / f"{nombre}_{i}.csv", sep=";", index=False, header=False)
print(f"{len(sel)} empresas en {partes} archivos: {T}/{nombre}_*.csv")
