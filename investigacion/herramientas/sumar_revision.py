"""Aplica las salidas de la revisión de alertas (instrucciones_revision.md) al CSV de prospectos.

Uso (desde la raíz del repo):
    PYTHONPATH=. python investigacion/herramientas/sumar_revision.py "alerta1_out*.csv" "revisión de alertas 29-09"
- descartar: la empresa va a datos/revisiones.csv y sale del CSV de prospectos (se guarda en
  investigacion/tandas/descartadas_revision.csv).
- mantener: se borra la alerta (pasa a la nota) y se reemplazan los datos que el agente trajo con fuente.
  Un decisor reemplazado pasa a otros_contactos.
- dudoso: queda la alerta, con lo que el agente averiguó en la nota.
"""
import glob
import sys
from pathlib import Path

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

T = Path("investigacion/tandas")
DEST = "canal/respuestas/20260926-prospectos-AB.csv"
REV = "datos/revisiones.csv"
ARCHIVO = T / "descartadas_revision.csv"
patron, etiqueta = sys.argv[1], sys.argv[2]

salidas = pd.concat([pd.read_csv(f, sep=";", dtype=str) for f in sorted(glob.glob(str(T / patron)))],
                    ignore_index=True).fillna("")
p = pd.read_csv(DEST, sep=";", dtype=str).fillna("")
rev = pd.read_csv(REV, sep=";", dtype=str).fillna("")
clave = p["razon_social"].map(nombre_normalizado)


def sumar(i, col, texto, sep=" | "):
    if texto:
        p.at[i, col] = f"{p.at[i, col]}{sep}{texto}" if p.at[i, col] else texto


fuera, resumen = [], {"mantener": 0, "descartar": 0, "dudoso": 0}
for _, s in salidas.iterrows():
    m = clave == nombre_normalizado(s["razon_social"])
    if m.sum() != 1:
        print(f"aviso: {s['razon_social']!r} aparece {m.sum()} veces en prospectos, se saltea")
        continue
    i = p.index[m][0]
    decision = s["decision"].strip().lower()
    resumen[decision] = resumen.get(decision, 0) + 1
    sumar(i, "fuente_enriquecimiento", s["fuente"])
    if decision == "descartar":
        if not (rev["razon_social"] == p.at[i, "razon_social"]).any():
            rev.loc[len(rev)] = [p.at[i, "razon_social"], "descartar", f"{s['motivo']} ({etiqueta})"]
        sumar(i, "nota", f"descartada en {etiqueta}: {s['motivo']}")
        fuera.append(p.loc[i].copy())
        continue
    if decision == "mantener":
        vieja = p.at[i, "alerta"]
        p.at[i, "alerta"] = ""
        sumar(i, "nota", f"revisada en {etiqueta}, se mantiene: {s['motivo']}"
                         + (f" (alerta anterior: {vieja})" if vieja else ""))
    else:
        sumar(i, "nota", f"{etiqueta}, sigue en duda: {s['motivo']}")
    if s["contacto_nombre"] and s["contacto_nombre"] != p.at[i, "contacto_nombre"]:
        if p.at[i, "contacto_nombre"]:
            sumar(i, "otros_contactos", f"{p.at[i, 'contacto_nombre']} ({p.at[i, 'contacto_cargo']}, dato anterior)", " / ")
        p.at[i, "contacto_cargo"] = ""  # el cargo viejo no corresponde al decisor nuevo
    for col_s, col_p in [("contacto_nombre", "contacto_nombre"), ("contacto_cargo", "contacto_cargo"),
                         ("contacto_email", "contacto_email"), ("contacto_telefono", "contacto_telefono"),
                         ("empleados", "empleados_aprox")]:
        if s[col_s]:
            p.at[i, col_p] = s[col_s]
    if p.at[i, "contacto_telefono"]:
        p.at[i, "verificar_no_llame"] = "sí"  # Registro «No Llame» (Ley 26.951)
    sumar(i, "nota", s["nota"])

if fuera:
    p = p.drop(index=[f.name for f in fuera])
    nuevas = pd.DataFrame(fuera)
    if ARCHIVO.exists():
        nuevas = pd.concat([pd.read_csv(ARCHIVO, sep=";", dtype=str).fillna(""), nuevas], ignore_index=True)
    nuevas.to_csv(ARCHIVO, sep=";", index=False, encoding="utf-8")
p.to_csv(DEST, sep=";", index=False, encoding="utf-8")
rev.to_csv(REV, sep=";", index=False, encoding="utf-8")
print(f"{resumen} | quedan {len(p)} prospectos, {(p['alerta'] != '').sum()} con alerta")
