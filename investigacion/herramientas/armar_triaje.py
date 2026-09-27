"""Arma lotes de nombres para el triaje por nombre (nivel 2 del embudo, sin búsquedas web).

Uso (desde la raíz del repo, después de `python -m prospeccion cartera`):
    PYTHONPATH=. python investigacion/herramientas/armar_triaje.py 250
Toma de la cartera unificada las empresas pendientes sin rubro que NO son personas físicas y que todavía no
tienen triaje, ordenadas por señal (email con dominio propio > teléfono > localidad), y deja
investigacion/triaje/lote_NN.csv (razon_social;localidad;dominio_email).
"""
import sys
from pathlib import Path

import pandas as pd
import yaml

from prospeccion.limpieza import nombre_normalizado

tam = int(sys.argv[1]) if len(sys.argv) > 1 else 250
T = Path("investigacion/triaje")
T.mkdir(parents=True, exist_ok=True)
gratuitos = set(yaml.safe_load(open("config.yaml"))["correo_gratuito"])
c = pd.read_csv("datos/salida/cartera_unificada.csv", sep=";", dtype=str).fillna("")
ya = set()
ruta_triaje = Path("datos/entrada/triaje.csv")
if ruta_triaje.exists():
    ya |= set(pd.read_csv(ruta_triaje, sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
for f in T.glob("lote_*.csv"):
    if "_out" not in f.name:
        ya |= set(pd.read_csv(f, sep=";", dtype=str)["razon_social"].map(nombre_normalizado))
s = c[(c["rubro_estado"] == "sin dato") & (c["estado_investigacion"] == "pendiente") & (c["persona_fisica"] != "sí")
      & ~c["razon_social"].map(nombre_normalizado).isin(ya)].copy()
dom = s["contacto_origen_email"].str.split(" / ").str[0].str.extract(r"@(.+)$")[0].fillna("").str.lower()
s["dominio_email"] = dom.where(~dom.isin(gratuitos), "")
s["_p"] = (s["dominio_email"] != "").astype(int) * 4 + (s["contacto_origen_telefono"] != "").astype(int) * 2 + (s["localidad"] != "").astype(int)
s = s.sort_values("_p", ascending=False)
print(f"para triar: {len(s)} (con dominio propio {int((s['dominio_email'] != '').sum())})")
existentes = len(list(T.glob("lote_[0-9]*.csv"))) - len(list(T.glob("lote_*_out.csv")))
for i in range(0, len(s), tam):
    n = existentes + i // tam
    s.iloc[i:i + tam][["razon_social", "localidad", "dominio_email"]].to_csv(T / f"lote_{n:02d}.csv", sep=";", index=False)
print(f"{(len(s) + tam - 1) // tam} lotes de hasta {tam} en {T}/lote_NN.csv")
