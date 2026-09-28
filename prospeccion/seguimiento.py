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


# --- Estados registrados en el tablero publicado ----------------------------------------------

def importar_estados(con: sqlite3.Connection, filas, ruta_bajas: str | Path | None = None) -> tuple[int, int]:
    """Pasa al seguimiento los estados que se marcaron en el tablero (CSV exportado o base del artefacto).

    Cada fila trae razon_social, localidad, estado, canal, quien, fecha y nota. Se une a la empresa por
    nombre normalizado y localidad (o solo por nombre si no hay otra igual). Un estado ya cargado con la
    misma fecha no se repite. «baja» y «figura_no_llame» van a datos/bajas.csv para siempre.
    Devuelve (interacciones nuevas, bajas nuevas).
    """
    from .limpieza import nombre_normalizado
    empresas = con.execute("SELECT id, razon_social, localidad, cuit, contacto_email, contacto_telefono, dominio_email FROM empresas").fetchall()
    por_clave: dict[str, list] = {}
    for e in empresas:
        por_clave.setdefault(f"{nombre_normalizado(e[1])}|{clave(e[2])}", []).append(e)
        por_clave.setdefault(nombre_normalizado(e[1]), []).append(e)
    nuevos = bajas = 0
    for f in filas:
        estado = clave(f.get("estado"))
        if estado not in RESULTADOS:
            continue
        candidatas = por_clave.get(f"{nombre_normalizado(f.get('razon_social'))}|{clave(f.get('localidad'))}") \
            or por_clave.get(nombre_normalizado(f.get("razon_social"))) or []
        if len({c[0] for c in candidatas}) != 1:
            continue  # sin empresa o con homónimas: no se adivina
        e = candidatas[0]
        fecha = str(f.get("fecha") or datetime.now().isoformat(timespec="seconds"))[:19]
        nota = " · ".join(x for x in (str(f.get("quien") or "").strip(), str(f.get("nota") or "").strip()) if x)
        ya = con.execute("SELECT 1 FROM interacciones WHERE empresa_id = ? AND resultado = ? AND fecha = ?",
                         (e[0], estado, fecha)).fetchone()
        if ya:
            continue
        con.execute("INSERT INTO interacciones (empresa_id, fecha, canal, resultado, nota, proximo_paso) VALUES (?,?,?,?,?,?)",
                    (e[0], fecha, str(f.get("canal") or "tablero"), estado, nota, ""))
        con.execute("UPDATE empresas SET estado = ? WHERE id = ?", (_TRANSICION[estado], e[0]))
        nuevos += 1
        if ruta_bajas and estado == "baja":
            existentes = leer_bajas(ruta_bajas)
            for tipo, valor in zip(("cuit", "email", "telefono", "dominio"), e[3:7]):
                if valor and clave(valor) not in existentes:
                    agregar_baja(ruta_bajas, tipo, valor, nota or "baja desde el tablero"); bajas += 1
        if ruta_bajas and estado == "figura_no_llame" and e[5] and clave(e[5]) not in leer_bajas(ruta_bajas):
            agregar_baja(ruta_bajas, "telefono", e[5], "Registro No Llame"); bajas += 1
    con.commit()
    return nuevos, bajas
