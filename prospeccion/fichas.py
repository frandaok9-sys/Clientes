"""Fichas de investigación profunda (JSON Lines) → enriquecimiento para el puntaje + hoja de ranking."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .limpieza import clave, nombre_normalizado, vacio

COLUMNAS_FICHA = [
    "encaje_coi", "plan_sugerido", "que_hace", "clientes_y_mercados", "dolor_probable", "angulo",
    "encaje_razon", "riesgos", "sistemas_actuales", "decisor_nombre", "decisor_cargo", "decisor_fuente",
    "email_empresa", "telefono_empresa", "web", "linkedin", "encontrada",
]


def _texto(valor) -> str:
    if isinstance(valor, list):
        return " | ".join(str(v) for v in valor if v)
    return "" if valor is None else str(valor)


def leer_fichas(carpeta: str | Path) -> pd.DataFrame:
    """Lee todas las fichas *.jsonl de la carpeta. Las líneas mal formadas se saltean con aviso."""
    filas = []
    for ruta in sorted(Path(carpeta).glob("*.jsonl")):
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if not linea.strip():
                continue
            try:
                filas.append({k: _texto(v) for k, v in json.loads(linea).items()} | {"_archivo": ruta.name})
            except json.JSONDecodeError:
                print(f"Aviso: {ruta.name}:{n} no es JSON válido, se saltea")
    df = pd.DataFrame(filas)
    if df.empty:
        return df
    # Las que un agente no llegó a investigar (tope de búsquedas) no cuentan como fichas: vuelven a la cola
    razon = df.get("encaje_razon", pd.Series("", index=df.index)).fillna("").str.lower()
    sin = (df.get("encontrada", pd.Series("", index=df.index)).fillna("").str.lower() == "no") & \
        razon.str.contains(r"(?:sin|no) investigad|investigar(?:la|las)? de nuevo|reprocesar|no se investig|sin investigar")
    df = df[~sin]
    df["encaje_coi"] = pd.to_numeric(df.get("encaje_coi"), errors="coerce")
    return df


def a_enriquecimiento(fichas: pd.DataFrame) -> pd.DataFrame:
    """Convierte fichas al formato de enriquecimiento que entiende `procesar` (une por razón social + localidad)."""
    out = pd.DataFrame({
        "razon_social": fichas["razon_social"],
        "localidad": fichas["localidad"],
        "web": fichas.get("web"),
        "rubro": fichas.get("rubro"),
        "empleados": fichas.get("empleados"),
        "senales": fichas.get("senales"),
        "contacto_nombre": fichas.get("decisor_nombre"),
        "contacto_cargo": fichas.get("decisor_cargo"),
        "email": fichas.get("email_empresa"),
        "telefono": fichas.get("telefono_empresa"),
        "fuente_enriquecimiento": fichas.get("fuentes"),
    })
    return out.replace("", pd.NA)


def unir_ranking(entrega: pd.DataFrame, fichas: pd.DataFrame) -> pd.DataFrame:
    """Tabla de prospectos investigados, ordenada por encaje con COI y después por puntaje del brief."""
    if fichas.empty:
        return pd.DataFrame()
    f = fichas.copy()
    f["_k"] = f["razon_social"].map(nombre_normalizado) + "|" + f["localidad"].map(clave)
    e = entrega.copy()
    e["_k"] = e["razon_social"].map(nombre_normalizado) + "|" + e["localidad"].map(clave)
    base = ["razon_social", "localidad", "provincia", "rubro_coi", "empleados_aprox", "puntaje", "categoria",
            "motivo_descarte", "contacto_email", "contacto_telefono", "verificar_no_llame"]
    r = e[base + ["_k"]].merge(f[[c for c in COLUMNAS_FICHA if c in f.columns] + ["_k"]], on="_k", how="inner")
    r["puntaje"] = pd.to_numeric(r["puntaje"], errors="coerce")
    # Una empresa descartada por las reglas no sube en el ranking aunque la ficha la puntúe alto
    r["_orden"] = r["encaje_coi"].where(r["categoria"] != "Descartada", -1)
    r = r.sort_values(["_orden", "puntaje"], ascending=False).drop(columns=["_k", "_orden"])
    r.insert(0, "ranking", range(1, len(r) + 1))
    return r.reset_index(drop=True)
