"""Anota descartes a mano en datos/revisiones.csv buscando la razón social exacta en las salidas de una tanda.

Uso (desde la raíz del repo):
    PYTHONPATH=. python investigacion/herramientas/descartar.py "q4_out*.csv" "pasada rápida q4" "Vazquez Hnos=minorista" ...
Cada argumento después de la etiqueta es «parte única del nombre=motivo». No toca el CSV de prospectos: para sacar
del tablero una empresa ya investigada, usar sumar_revision.py.
"""
import glob
import sys

import pandas as pd

patron, etiqueta, pares = sys.argv[1], sys.argv[2], sys.argv[3:]
salidas = pd.concat([pd.read_csv(f, sep=";", dtype=str) for f in sorted(glob.glob(f"investigacion/tandas/{patron}"))],
                    ignore_index=True).fillna("")
rev = pd.read_csv("datos/revisiones.csv", sep=";", dtype=str).fillna("")
for par in pares:
    parte, motivo = par.split("=", 1)
    m = salidas[salidas["razon_social"].str.contains(parte, case=False, regex=False)].drop_duplicates("razon_social")
    if len(m) != 1:
        sys.exit(f"«{parte}» coincide con {len(m)} empresas: usá una parte más precisa")
    razon = m.iloc[0]["razon_social"]
    if (rev["razon_social"] == razon).any():
        print(f"ya estaba: {razon}")
        continue
    rev.loc[len(rev)] = [razon, "descartar", f"{motivo} ({etiqueta})"]
    print(f"descartada: {razon} | {motivo}")
rev.to_csv("datos/revisiones.csv", sep=";", index=False, encoding="utf-8")
