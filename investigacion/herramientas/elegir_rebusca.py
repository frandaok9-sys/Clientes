"""Elige empresas ya investigadas a las que les falta decisor o canal y las reparte para una segunda búsqueda.

Uso (desde la raíz del repo):
    PYTHONPATH=. python investigacion/herramientas/elegir_rebusca.py r1 96 8
Deja investigacion/tandas/r1_0.csv ... r1_7.csv (con encabezado: llevan lo que ya se sabe).
Orden: A, B sin alerta, B con alerta, C sin alerta, C con alerta. No repite empresas de rebúsquedas anteriores.
"""
import glob
import sys
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

nombre, cantidad, partes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = Path("investigacion/tandas")
p = pd.read_csv("canal/respuestas/20260926-prospectos-AB.csv", sep=";", dtype=str).fillna("")
hechas = set()
for f in glob.glob(str(T / "r*_[0-9]*.csv")):
    if "_out" not in f:
        hechas |= set(pd.read_csv(f, sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
decisor = p["contacto_nombre"] != ""
canal = (p["contacto_email"] != "") | (p["contacto_telefono"] != "")
p["falta"] = ["decisor y canal" if not d and not c else "decisor" if not d else "canal" if not c else ""
              for d, c in zip(decisor, canal)]
p["_orden"] = p["categoria"].map({"A": 0, "B": 1, "C": 3}).fillna(4) + (p["alerta"] != "").astype(int)
sel = p[(p["falta"] != "") & ~p["razon_social"].map(nombre_normalizado).isin(hechas)].sort_values(["_orden", "puntaje"], ascending=[True, False])
print(f"con datos faltantes: {len(sel)} ({sel['falta'].value_counts().to_dict()})")
sel = sel.head(cantidad)[["razon_social", "localidad", "nombre_corto", "web", "rubro", "contacto_nombre", "contacto_cargo",
                          "contacto_email", "contacto_telefono", "falta"]]
for i in range(partes):
    sel.iloc[i::partes].to_csv(T / f"{nombre}_{i}.csv", sep=";", index=False)
print(f"{len(sel)} empresas en {partes} archivos: {T}/{nombre}_*.csv")
