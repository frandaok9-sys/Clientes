"""Tablero visual de prospectos: divide las empresas por qué tan listas están para contactar."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

CARRILES = [
    ("listas", "Decisor y canal", "Hay una persona con cargo y un email o teléfono publicado. Se contactan primero."),
    ("generico", "Solo canal de la empresa", "Hay email o teléfono, pero no un decisor confirmado. Pedí por el dueño o el gerente."),
    ("sin_canal", "Sin canal publicado", "No publican email ni teléfono. Llamá al conmutador o buscá el dato en la próxima ronda."),
    ("revisar", "Revisar antes", "Hay una alerta de tamaño, rubro o situación. Decidí si se contactan."),
]


def carril(f: pd.Series) -> str:
    if f.get("alerta"):
        return "revisar"
    canal = bool(f.get("contacto_email") or f.get("contacto_telefono"))
    if not canal:
        return "sin_canal"
    return "listas" if f.get("contacto_nombre") else "generico"


def datos(df: pd.DataFrame) -> list[dict]:
    df = df.fillna("")
    df["carril"] = df.apply(carril, axis=1)
    campos = ["razon_social", "nombre_corto", "localidad", "categoria", "rubro_coi", "plan_sugerido", "web",
              "madurez_digital", "contacto_nombre", "contacto_cargo", "contacto_email", "contacto_telefono",
              "otros_contactos", "empleados_aprox", "dato", "alerta", "nota", "borrador", "carril"]
    if "puntaje" in df:
        df["_p"] = pd.to_numeric(df["puntaje"], errors="coerce").fillna(0)
    else:
        df["_p"] = 0
    df = df.sort_values(["categoria", "_p", "razon_social"], ascending=[True, False, True])
    return [{c: str(f.get(c, "")) for c in campos} for _, f in df.iterrows()]


def generar(csv: Path, salida: Path, titulo: str = "Prospectos COI") -> Path:
    df = pd.read_csv(csv, sep=";", dtype=str)
    plantilla = (Path(__file__).parent / "tablero.html").read_text(encoding="utf-8")
    pagina = (plantilla.replace("__TITULO__", html.escape(titulo))
              .replace("__CARRILES__", json.dumps(CARRILES, ensure_ascii=False))
              .replace("__DATOS__", json.dumps(datos(df), ensure_ascii=False).replace("</", "<\\/")))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(pagina, encoding="utf-8")
    return salida
