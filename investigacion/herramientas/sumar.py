"""Califica las empresas que devolvieron los agentes y las suma a canal/respuestas/20260926-prospectos-AB.csv.

Uso (desde la raíz del repo, con el entorno activado):
    PYTHONPATH=. python investigacion/herramientas/sumar.py "t5_out*.csv"
"""
import csv, glob, sys
import pandas as pd, yaml
from prospeccion import clasificacion, limpieza, mensajes
from investigacion.herramientas.comun import borrador
S = "investigacion/tandas"  # CSV que devuelven los agentes
DEST = "canal/respuestas/20260926-prospectos-AB.csv"
cfg = yaml.safe_load(open("config.yaml"))


nuevas = pd.concat([pd.read_csv(f, sep=";", dtype=str) for f in sorted(glob.glob(f"{S}/" + (sys.argv[1] if len(sys.argv) > 1 else "nueva_out0*.csv")))], ignore_index=True).fillna("")
orig = nuevas.copy()
df = nuevas.rename(columns={"contacto_email": "email", "contacto_telefono": "telefono"})
df = limpieza.mapear_columnas(df, cfg["columnas"])
df = limpieza.limpiar(df, "AR")
cal = clasificacion.calificar(df, cfg, set(), verificar_mx=False)
gratuitos = set(cfg["correo_gratuito"]); genericos = cfg["emails_genericos"]
R = {r["nombre"]: r for r in cfg["rubros"]}; GEN = cfg["industrial_generico"]
viejas = pd.read_csv(DEST, sep=";", dtype=str).fillna("")
cols = list(viejas.columns)
filas, descartadas = [], []
for _, f in cal.iterrows():
    o = orig[orig["razon_social"] == f["razon_social"]].iloc[0]
    if f["razon_social"] in set(viejas["razon_social"]):
        continue
    if f["categoria"] == "Descartada" or (o["alerta"] and f["categoria"] in ("C", "C - chico") and not o["contacto_telefono"] and not o["contacto_email"]):
        descartadas.append((f["razon_social"], f["motivo_descarte"] if f["categoria"] == "Descartada" else o["alerta"])); continue
    if not o["web"] and not o["contacto_telefono"] and not o["contacto_email"] and not o["contacto_nombre"] and not o["dato"]:
        descartadas.append((f["razon_social"], "no se encontró nada")); continue
    r = R.get(f["rubro_coi"], GEN)
    corto, b = borrador(o, r, cfg)
    email = o["contacto_email"]
    propio = bool(email) and email.split("@")[-1].lower() not in gratuitos
    filas.append({"razon_social": o["razon_social"], "nombre_corto": corto, "localidad": o["localidad"], "rubro": o["rubro"],
        "categoria": f["categoria"], "rubro_coi": f["rubro_coi"] if isinstance(f["rubro_coi"], str) else "Industrial B2B",
        "plan_sugerido": r.get("plan", GEN["plan"]), "web": o["web"],
        "madurez_digital": {2: "alta", 1: "media", 0: "baja"}[bool(o["web"]) + propio],
        "contacto_nombre": o["contacto_nombre"], "contacto_cargo": o["contacto_cargo"], "contacto_email": email,
        "contacto_telefono": o["contacto_telefono"], "verificar_no_llame": "sí" if o["contacto_telefono"] else "",
        "otros_contactos": o["otros_contactos"], "empleados_aprox": o["empleados"], "senales": o["senales"], "dato": dato,
        "alerta": o["alerta"], "nota": o["nota"], "borrador": b, "fuente": "búsqueda web (sesión cloud)",
        "fuente_enriquecimiento": o["fuente_enriquecimiento"], "fecha_revision": "2026-09-26", "puntaje": str(f["puntaje"])})
nuevo = pd.DataFrame(filas)
if "puntaje" not in cols: cols.insert(cols.index("categoria") + 1, "puntaje")
todo = pd.concat([viejas, nuevo], ignore_index=True).reindex(columns=cols).fillna("")
todo.to_csv(DEST, sep=";", index=False, encoding="utf-8")
print("sumadas:", len(nuevo), nuevo["categoria"].value_counts().to_dict())
print("madurez:", nuevo["madurez_digital"].value_counts().to_dict())
print("descartadas:"); [print(" -", a, "|", b) for a, b in descartadas]
