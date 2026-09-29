"""Suma las salidas de la pasada rápida de rubro a canal/respuestas/20260927-rubro-rapido.csv.

Uso: PYTHONPATH=. python investigacion/herramientas/sumar_rapida.py "q1_out*.csv"
`python -m prospeccion todo` lee ese CSV como una fuente más: el rubro confirmado manda sobre el nombre, y una
alerta de descarte (en `senales`) descarta la empresa. La cartera lo muestra como rubro verificado (pasada rápida).
"""
import glob
import sys

import pandas as pd

from prospeccion.limpieza import nombre_normalizado

S = "investigacion/tandas"
DEST = "canal/respuestas/20260927-rubro-rapido.csv"
COLS = ["razon_social", "localidad", "provincia", "web", "rubro", "empleados", "senales", "alerta", "fuente_enriquecimiento", "fuente", "fecha_revision"]
nuevas = pd.concat([pd.read_csv(f, sep=";", dtype=str) for f in sorted(glob.glob(f"{S}/" + sys.argv[1]))], ignore_index=True).fillna("")
nuevas = nuevas.rename(columns={"fuente": "fuente_enriquecimiento"})
# Sin URL no hay dato verificado: la fila queda solo como "pasada, sin resultado"
sin_url = nuevas["fuente_enriquecimiento"].str.strip() == ""
nuevas.loc[sin_url, ["web", "rubro", "empleados", "senales"]] = ""
nuevas.loc[sin_url & (nuevas["alerta"] == ""), "alerta"] = "sin fuente: no se pudo confirmar"
nuevas["senales"] = [" | ".join(x for x in (s, a) if x) for s, a in zip(nuevas["senales"], nuevas["alerta"])]
nuevas["fuente"] = "pasada rápida de rubro"
nuevas["fecha_revision"] = pd.Timestamp.today().strftime("%Y-%m-%d")
try:
    viejas = pd.read_csv(DEST, sep=";", dtype=str).fillna("")
except FileNotFoundError:
    viejas = pd.DataFrame(columns=COLS)
todo = pd.concat([viejas, nuevas.reindex(columns=COLS).fillna("")], ignore_index=True)
todo = todo[~todo["razon_social"].map(nombre_normalizado).duplicated(keep="last")]
todo.to_csv(DEST, sep=";", index=False, encoding="utf-8")
con_rubro = (nuevas["rubro"] != "").sum()
print(f"pasada rápida: {len(nuevas)} nuevas ({con_rubro} con rubro confirmado, {(nuevas['alerta'] != '').sum()} con alerta); total {len(todo)} -> {DEST}")
