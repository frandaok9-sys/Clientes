"""Completa vacíos de prospectos ya investigados con lo que devolvió una rebúsqueda. Nunca pisa un dato ni agrega filas.

Uso (desde la raíz del repo, con el entorno activado):
    PYTHONPATH=. python investigacion/herramientas/completar.py "r1_out*.csv"
"""
import glob
import sys

import pandas as pd
import yaml

from investigacion.herramientas.comun import borrador
from prospeccion.limpieza import nombre_normalizado

S = "investigacion/tandas"
DEST = "canal/respuestas/20260926-prospectos-AB.csv"
CAMPOS = ["contacto_nombre", "contacto_cargo", "contacto_email", "contacto_telefono", "otros_contactos"]
cfg = yaml.safe_load(open("config.yaml"))
R = {r["nombre"]: r for r in cfg["rubros"]}
GEN = cfg["industrial_generico"]
gratuitos = set(cfg["correo_gratuito"])

nuevas = pd.concat([pd.read_csv(f, sep=";", dtype=str) for f in sorted(glob.glob(f"{S}/" + sys.argv[1]))], ignore_index=True).fillna("")
p = pd.read_csv(DEST, sep=";", dtype=str).fillna("")
p["_k"] = p["razon_social"].map(nombre_normalizado)
hoy = pd.Timestamp.today().strftime("%Y-%m-%d")
completadas, sin_novedad, sin_fuente = [], [], []
for _, n in nuevas.iterrows():
    idx = p.index[p["_k"] == nombre_normalizado(n["razon_social"])]
    if len(idx) == 0:
        print("no está en prospectos:", n["razon_social"]); continue
    i = idx[0]
    aportes = {c: n[c].strip() for c in CAMPOS if n[c].strip() and not p.at[i, c].strip()}
    if aportes and not n["fuente"].strip():
        sin_fuente.append(n["razon_social"]); aportes = {}  # sin URL no entra nada
    if not aportes:
        if n["nota"].strip():
            p.at[i, "nota"] = " | ".join(x for x in (p.at[i, "nota"], "rebúsqueda: " + n["nota"].strip()) if x)
        sin_novedad.append(n["razon_social"]); continue
    for c, v in aportes.items():
        p.at[i, c] = v
    if n["nota"].strip():
        p.at[i, "nota"] = " | ".join(x for x in (p.at[i, "nota"], "rebúsqueda: " + n["nota"].strip()) if x)
    fuentes = dict.fromkeys(x for x in (p.at[i, "fuente_enriquecimiento"] + " | " + n["fuente"]).split(" | ") if x)
    p.at[i, "fuente_enriquecimiento"] = " | ".join(fuentes)
    p.at[i, "fecha_revision"] = hoy
    if p.at[i, "contacto_telefono"]:
        p.at[i, "verificar_no_llame"] = "sí"
    email = p.at[i, "contacto_email"]
    propio = bool(email) and email.split("@")[-1].lower() not in gratuitos
    p.at[i, "madurez_digital"] = {2: "alta", 1: "media", 0: "baja"}[bool(p.at[i, "web"]) + propio]
    o = p.loc[i].copy(); o["dato"] = o["dato"].rstrip(". ")
    _, p.at[i, "borrador"] = borrador(o, R.get(p.at[i, "rubro_coi"], GEN), cfg)
    completadas.append((n["razon_social"], ", ".join(aportes)))
p.drop(columns=["_k"]).to_csv(DEST, sep=";", index=False, encoding="utf-8")
print(f"completadas: {len(completadas)}"); [print(" +", a, "|", b) for a, b in completadas]
print(f"sin novedad: {len(sin_novedad)}")
if sin_fuente:
    print("descartado por venir sin URL de fuente:", ", ".join(sin_fuente))
