"""Junta las salidas del triaje por nombre en datos/entrada/triaje.csv (el pipeline lo usa para ordenar la cola).

Uso: PYTHONPATH=. python investigacion/herramientas/sumar_triaje.py
Solo acepta las cuatro clases; una fila con otra cosa se descarta con aviso. El triaje ordena, no califica.
"""
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import clave, nombre_normalizado

CLASES = {"industrial_objetivo", "industrial_otro", "indeterminado", "no_objetivo"}
T = Path("investigacion/triaje")
DEST = Path("datos/entrada/triaje.csv")
marcos = []
for f in sorted(T.glob("lote_*_out.csv")):
    try:
        d = pd.read_csv(f, sep=";", dtype=str).fillna("")
    except Exception as e:
        print(f"aviso: {f.name} no se pudo leer ({e})"); continue
    if not {"razon_social", "localidad", "triaje"} <= set(d.columns):
        print(f"aviso: {f.name} sin las columnas esperadas"); continue
    d["triaje"] = d["triaje"].str.strip().str.lower()
    malas = ~d["triaje"].isin(CLASES)
    if malas.any():
        print(f"aviso: {f.name}: {int(malas.sum())} filas con clase inválida, se saltean")
    marcos.append(d[~malas][["razon_social", "localidad", "triaje", "motivo"]] if "motivo" in d.columns else d[~malas].assign(motivo=""))
if DEST.exists():
    marcos.insert(0, pd.read_csv(DEST, sep=";", dtype=str).fillna(""))
todo = pd.concat(marcos, ignore_index=True) if marcos else pd.DataFrame(columns=["razon_social", "localidad", "triaje", "motivo"])
todo["_k"] = todo["razon_social"].map(nombre_normalizado) + "|" + todo["localidad"].map(clave)
todo = todo.drop_duplicates("_k", keep="last").drop(columns="_k")
DEST.parent.mkdir(parents=True, exist_ok=True)
todo.to_csv(DEST, sep=";", index=False, encoding="utf-8")
print(f"triaje: {len(todo)} empresas -> {DEST}")
print(todo["triaje"].value_counts().to_dict())
