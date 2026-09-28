"""Elige empresas para la pasada rápida de rubro (nivel 3 del embudo) y las reparte entre agentes.

Uso (desde la raíz del repo, después de `python -m prospeccion todo`):
    PYTHONPATH=. python investigacion/herramientas/elegir_rapida.py q1 240 8
Toma de candidatos_enriquecer.csv las que no tienen rubro detectado y cuyo triaje es industrial_objetivo
(primero) o industrial_otro, sin repetir las ya investigadas o ya pasadas. Deja investigacion/tandas/q1_i.csv (sin encabezado).
"""
import glob
import sys
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

nombre, cantidad, partes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = Path("investigacion/tandas")
c = pd.read_csv("datos/salida/candidatos_enriquecer.csv", sep=";", dtype=str).fillna("")
hechas = set()
for f in glob.glob("canal/respuestas/*.csv") + glob.glob(str(T / "*_out*.csv")):
    d = pd.read_csv(f, sep=";", dtype=str)
    if "razon_social" in d.columns:
        hechas |= set(d["razon_social"].map(nombre_normalizado))
for f in glob.glob(str(T / "[tq]*_[0-9]*.csv")):
    if "_out" not in f:
        hechas |= set(pd.read_csv(f, sep=";", dtype=str, header=None)[0].map(nombre_normalizado))
c = c[~c["razon_social"].map(nombre_normalizado).isin(hechas) & (c["rubro_coi"] == "")
      & c["triaje"].isin(["industrial_objetivo", "industrial_otro"])]
c = c.assign(_o=c["triaje"].map({"industrial_objetivo": 1, "industrial_otro": 0}),
             _p=c["prioridad_enriquecimiento"].astype(int)).sort_values(["_o", "_p"], ascending=False)
print(f"quedan {len(c)} para pasada rápida ({c['triaje'].value_counts().to_dict()})")
sel = c.head(cantidad).rename(columns={"dominio_email": "dominio_conocido"})[["razon_social", "localidad", "provincia", "dominio_conocido"]]
for i in range(partes):
    sel.iloc[i::partes].to_csv(T / f"{nombre}_{i}.csv", sep=";", index=False, header=False)
print(f"{len(sel)} empresas en {partes} archivos: {T}/{nombre}_*.csv")
