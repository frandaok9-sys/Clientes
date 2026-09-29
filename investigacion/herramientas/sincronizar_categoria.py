"""Copia al CSV de prospectos la categoría y el puntaje recalculados por `python -m prospeccion todo`.

El tablero lee canal/respuestas/20260926-prospectos-AB.csv, que conserva la categoría del momento en que se sumó
cada tanda. `todo` recalcula con todas las fuentes (rebúsquedas, pasadas rápidas, MX), así que la entrega manda.
Uso (desde la raíz del repo, después de `todo`):
    PYTHONPATH=. python investigacion/herramientas/sincronizar_categoria.py
Solo toca A, B y C; una empresa descartada en la entrega se informa pero no se saca (eso es sumar_revision.py).
"""
import pandas as pd

from prospeccion.limpieza import nombre_normalizado

DEST = "canal/respuestas/20260926-prospectos-AB.csv"
e = pd.read_csv("datos/salida/entrega.csv", sep=";", dtype=str).fillna("")
p = pd.read_csv(DEST, sep=";", dtype=str).fillna("")
e = e.assign(k=e["razon_social"].map(nombre_normalizado)).drop_duplicates("k").set_index("k")
cambios, raras = [], []
for i, fila in p.iterrows():
    k = nombre_normalizado(fila["razon_social"])
    if k not in e.index:
        continue
    cat, pts = e.at[k, "categoria"], e.at[k, "puntaje"]
    if cat not in ("A", "B", "C"):
        raras.append(f"{fila['razon_social']}: {cat} ({e.at[k, 'motivo_descarte']})")
        continue
    if (cat, pts) != (fila["categoria"], fila["puntaje"]):
        cambios.append((fila["categoria"], cat))
        p.at[i, "categoria"], p.at[i, "puntaje"] = cat, pts
p.to_csv(DEST, sep=";", index=False, encoding="utf-8")
resumen = pd.Series([f"{a}->{b}" for a, b in cambios if a != b]).value_counts().to_dict()
print(f"{len(cambios)} filas actualizadas; cambios de categoría: {resumen}")
for r in raras:
    print(f"en la entrega no es A/B/C: {r}")
print("categorías en el tablero:", p["categoria"].value_counts().to_dict())
