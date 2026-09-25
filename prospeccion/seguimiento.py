"""Registro de contactos (llamadas, mensajes) y estado del pipeline en SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

ESTADOS = [
    "pendiente", "contactado", "sin_respuesta", "interesado",
    "reunion", "propuesta", "ganado", "perdido", "no_contactar",
]
RESULTADOS = ["sin_respuesta", "buzon", "interesado", "no_interesado", "volver_a_llamar", "reunion", "numero_erroneo"]

# Estado al que pasa el cliente según el resultado del contacto
_TRANSICION = {
    "sin_respuesta": "sin_respuesta",
    "buzon": "sin_respuesta",
    "interesado": "interesado",
    "no_interesado": "perdido",
    "volver_a_llamar": "contactado",
    "reunion": "reunion",
    "numero_erroneo": "no_contactar",
}


def conectar(ruta: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(ruta)
    con.execute("""
        CREATE TABLE IF NOT EXISTS interacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            canal TEXT NOT NULL,
            resultado TEXT NOT NULL,
            nota TEXT,
            proximo_paso TEXT
        )""")
    return con


def hay_seguimiento(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT COUNT(*) FROM interacciones").fetchone()[0] > 0


def guardar_clientes(df: pd.DataFrame, con: sqlite3.Connection) -> None:
    """Reemplaza la lista de clientes y borra el historial (los IDs cambian al reprocesar)."""
    con.execute("DELETE FROM interacciones")
    df = df.copy()
    df.insert(0, "id", range(1, len(df) + 1))
    df.to_sql("clientes", con, if_exists="replace", index=False)
    con.commit()


def registrar(con: sqlite3.Connection, cliente_id: int, canal: str, resultado: str,
              nota: str = "", proximo_paso: str = "") -> str:
    if resultado not in RESULTADOS:
        raise ValueError(f"Resultado no válido. Usa uno de: {', '.join(RESULTADOS)}")
    if not con.execute("SELECT 1 FROM clientes WHERE id = ?", (cliente_id,)).fetchone():
        raise ValueError(f"No existe el cliente {cliente_id}")
    con.execute(
        "INSERT INTO interacciones (cliente_id, fecha, canal, resultado, nota, proximo_paso) VALUES (?,?,?,?,?,?)",
        (cliente_id, datetime.now().isoformat(timespec="seconds"), canal, resultado, nota, proximo_paso),
    )
    nuevo = _TRANSICION[resultado]
    con.execute("UPDATE clientes SET estado = ? WHERE id = ?", (nuevo, cliente_id))
    con.commit()
    return nuevo


def cola(con: sqlite3.Connection, canal: str | None = None, limite: int = 50) -> pd.DataFrame:
    """Siguientes clientes a contactar: pendientes o sin respuesta, por segmento y puntuación."""
    sql = """
        SELECT c.id, c.segmento AS seg, c.puntuacion AS pts, c.nombre, c.empresa, c.telefono, c.canal, c.estado,
               COUNT(i.id) AS intentos
        FROM clientes c LEFT JOIN interacciones i ON i.cliente_id = c.id
        WHERE c.estado IN ('pendiente', 'sin_respuesta', 'contactado')
    """
    params: list = []
    if canal:
        sql += " AND c.canal = ?"
        params.append(canal)
    sql += " GROUP BY c.id HAVING intentos < 4 ORDER BY c.segmento, COUNT(i.id), c.puntuacion DESC LIMIT ?"
    params.append(limite)
    return pd.read_sql_query(sql, con, params=params)


def resumen(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT segmento, estado, COUNT(*) AS clientes FROM clientes GROUP BY segmento, estado ORDER BY segmento, estado",
        con,
    )
