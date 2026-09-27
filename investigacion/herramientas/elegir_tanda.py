"""Elige la próxima tanda de candidatas a investigar y la reparte en N archivos para los agentes.

Uso (desde la raíz del repo, después de `python -m prospeccion todo`):
    PYTHONPATH=. python investigacion/herramientas/elegir_tanda.py t5 96 8
Deja investigacion/tandas/t5_0.csv ... t5_7.csv (sin encabezado).
"""
import glob
import sys
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

nombre, cantidad, partes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = Path("investigacion/tandas")
T.mkdir(parents=True, exist_ok=True)
c = pd.read_csv("datos/salida/candidatos_enriquecer.csv", sep=";", dtype=str).fillna("")
hechas = set()
for f in glob.glob("canal/pedidos/*.csv") + ["canal/respuestas/20260926-prospectos-AB.csv"] + glob.glob(str(T / "*_out*.csv")):
    hechas |= set(pd.read_csv(f, sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
for f in glob.glob(str(T / "t*_[0-9]*.csv")):
    if "_out" not in f:
        hechas |= set(pd.read_csv(f, sep=";", dtype=str, header=None)[0].map(nombre_normalizado))
# También por dominio: la misma empresa puede figurar en la cartera con dos nombres distintos
webs = set(pd.read_csv("canal/respuestas/20260926-prospectos-AB.csv", sep=";", dtype=str)["web"].dropna()) - {""}
c = c[~c["razon_social"].map(nombre_normalizado).isin(hechas) & ~c["fuente"].str.contains("búsqueda web")
      & ~c["dominio_email"].fillna("").isin(webs)]
c = c[c["rubro_coi"] != ""].assign(p=c["prioridad_enriquecimiento"].astype(int)).sort_values("p", ascending=False)
print(f"quedan {len(c)} candidatas con rubro detectado")
sel = c.head(cantidad).rename(columns={"dominio_email": "dominio_conocido", "rubro_coi": "rubro_supuesto"})[
    ["razon_social", "localidad", "provincia", "dominio_conocido", "rubro_supuesto"]]
for i in range(partes):
    sel.iloc[i::partes].to_csv(T / f"{nombre}_{i}.csv", sep=";", index=False, header=False)
print(f"{len(sel)} empresas en {partes} archivos: {T}/{nombre}_*.csv")
