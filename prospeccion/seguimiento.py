"""Seguimiento de contactos en SQLite y registro permanente de bajas."""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from .limpieza import clave

RESULTADOS = ["sin_respuesta", "buzon", "interesado", "no_interesado", "volver_a_llamar",
              "demo_agendada", "numero_erroneo", "figura_no_llame", "baja"]

_TRANSICION = {
    "sin_respuesta": "sin_respuesta",
    "buzon": "sin_respuesta",
    "interesado": "interesado",
    "no_interesado": "perdido",
    "volver_a_llamar": "contactado",
    "demo_agendada": "demo",
    "numero_erroneo": "no_contactar",
    "figura_no_llame": "no_llamar",
    "baja": "baja",
}


# --- Bajas (Ley 25.326: se respetan para siempre) ---------------------------------------------

def leer_bajas(ruta: str | Path) -> set[str]:
    ruta = Path(ruta)
    if not ruta.exists():
        return set()
    with open(ruta, encoding="utf-8", newline="") as f:
        return {clave(r["valor"]) for r in csv.DictReader(f, delimiter=";") if r.get("valor")}


def agregar_baja(ruta: str | Path, tipo: str, valor: str, nota: str = "") -> None:
    ruta = Path(ruta)
    nuevo = not ruta.exists() or ruta.stat().st_size == 0
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if nuevo:
            w.writerow(["tipo", "valor", "fecha", "nota"])
        w.writerow([tipo, valor, datetime.now().date().isoformat(), nota])


# --- Base de seguimiento ----------------------------------------------------------------------

def conectar(ruta: str | Path) -> sqlite3.Connection:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.execute("""
        CREATE TABLE IF NOT EXISTS interacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            canal TEXT NOT NULL,
            resultado TEXT NOT NULL,
            nota TEXT,
            proximo_paso TEXT
        )""")
    return con


def hay_seguimiento(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT COUNT(*) FROM interacciones").fetchone()[0] > 0


def guardar_empresas(df: pd.DataFrame, con: sqlite3.Connection) -> None:
    """Reemplaza la lista y borra el historial (los IDs cambian al reprocesar)."""
    con.execute("DELETE FROM interacciones")
    df = df[[c for c in df.columns if not c.startswith("_")]].copy()
    df.insert(0, "id", range(1, len(df) + 1))
    df["estado"] = "pendiente"
    df.to_sql("empresas", con, if_exists="replace", index=False)
    con.commit()


def registrar(con: sqlite3.Connection, empresa_id: int, canal: str, resultado: str,
              nota: str = "", proximo_paso: str = "", ruta_bajas: str | Path | None = None) -> str:
    if resultado not in RESULTADOS:
        raise ValueError(f"Resultado no válido. Usá uno de: {', '.join(RESULTADOS)}")
    fila = con.execute("SELECT cuit, contacto_email, contacto_telefono, dominio_email FROM empresas WHERE id = ?",
                       (empresa_id,)).fetchone()
    if not fila:
        raise ValueError(f"No existe la empresa {empresa_id}")
    con.execute(
        "INSERT INTO interacciones (empresa_id, fecha, canal, resultado, nota, proximo_paso) VALUES (?,?,?,?,?,?)",
        (empresa_id, datetime.now().isoformat(timespec="seconds"), canal, resultado, nota, proximo_paso),
    )
    nuevo = _TRANSICION[resultado]
    con.execute("UPDATE empresas SET estado = ? WHERE id = ?", (nuevo, empresa_id))
    con.commit()
    if ruta_bajas and resultado == "baja":
        for tipo, valor in zip(("cuit", "email", "telefono", "dominio"), fila):
            if valor:
                agregar_baja(ruta_bajas, tipo, valor, nota)
    if ruta_bajas and resultado == "figura_no_llame" and fila[2]:
        agregar_baja(ruta_bajas, "telefono", fila[2], "Registro No Llame")
    return nuevo


def cola(con: sqlite3.Connection, limite: int = 50) -> pd.DataFrame:
    """Siguientes empresas A/B a contactar, por categoría, intentos y puntaje."""
    sql = """
        SELECT e.id, e.categoria AS cat, e.puntaje AS pts, COALESCE(e.nombre_fantasia, e.razon_social) AS empresa,
               e.rubro_coi, e.contacto_nombre, e.contacto_telefono, e.estado,
               COUNT(i.id) AS intentos
        FROM empresas e LEFT JOIN interacciones i ON i.empresa_id = e.id
        WHERE e.categoria IN ('A', 'B') AND e.estado IN ('pendiente', 'sin_respuesta', 'contactado')
        GROUP BY e.id HAVING intentos < 4
        ORDER BY e.categoria, intentos, e.puntaje DESC LIMIT ?
    """
    return pd.read_sql_query(sql, con, params=[limite])


def resumen(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT categoria, estado, COUNT(*) AS empresas FROM empresas GROUP BY categoria, estado", con)
