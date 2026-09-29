"""Tablero de trabajo de prospectos: una lista ordenada por prioridad, detalle con acciones y estado por empresa.

La página guarda el estado de cada contacto (pendiente, interesado, demo, baja...) en la base del artefacto
publicado, compartida entre quienes lo abren. No envía nada: copia textos y arma el enlace de WhatsApp.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pandas as pd
import phonenumbers

from .limpieza import clave, nombre_normalizado, normalizar_telefono, vacio

# Estados que se registran desde el tablero. Las claves coinciden con seguimiento.RESULTADOS.
ESTADOS = [
    ("pendiente", "Pendiente", "abierta"),
    ("sin_respuesta", "Contactado, sin respuesta", "curso"),
    ("volver_a_llamar", "Volver a llamar", "curso"),
    ("interesado", "Interesado", "curso"),
    ("demo_agendada", "Demo agendada", "ganada"),
    ("no_interesado", "No interesado", "cerrada"),
    ("numero_erroneo", "Número erróneo", "cerrada"),
    ("figura_no_llame", "Figura en No Llame", "cerrada"),
    ("baja", "Pidió la baja", "cerrada"),
]

_ORDEN_CAT = {"A": 0, "B": 1, "C": 2}
_ORDEN_CARRIL = {"listas": 0, "generico": 1, "revisar": 2, "sin_canal": 3}


def carril(f: pd.Series) -> str:
    """listas: decisor y canal | generico: solo canal | revisar: hay alerta | sin_canal: nada publicado."""
    if f.get("alerta"):
        return "revisar"
    canal = bool(f.get("contacto_email") or f.get("contacto_telefono"))
    if not canal:
        return "sin_canal"
    return "listas" if f.get("contacto_nombre") else "generico"


def id_empresa(razon_social: str, localidad: str) -> str:
    """Identificador estable para la base del artefacto: solo letras, dígitos, «-» y «~»."""
    n = nombre_normalizado(razon_social).replace(" ", "-") or "sin-nombre"
    loc = re.sub(r"[^a-z0-9]+", "-", clave(localidad)).strip("-")
    return f"{n}~{loc}" if loc else n


def telefono_e164(texto: str) -> str:
    """Primer número del campo, en E.164, sin las aclaraciones entre paréntesis. Vacío si no es válido."""
    if vacio(texto):
        return ""
    limpio = re.sub(r"\([^)]*[A-Za-z][^)]*\)", " ", str(texto))
    primero = re.split(r"\s*(?:/|\||\by\b|;)\s*", limpio)[0]
    return normalizar_telefono(primero, "AR") or ""


_ETIQUETA_WA = re.compile(r"whats|wsp|wpp|celular|\bcel\b|m[oó]vil", re.IGNORECASE)


def whatsapp_e164(texto: str) -> str:
    """Número para el enlace de WhatsApp: el primero marcado como WhatsApp o celular, o si no el primer celular.

    Un fijo común no tiene WhatsApp, así que un número sin marca solo sirve si es celular (en la Argentina, con
    el 9 después del 54). Un número que la fuente marca como WhatsApp se usa tal como vino, aunque parezca fijo:
    puede ser un fijo con WhatsApp Business y no se le agregan dígitos.
    """
    if vacio(texto):
        return ""
    celulares = []
    for tramo in re.split(r"\s*(?:/|\||\by\b|;)\s*", str(texto)):
        marcado = bool(_ETIQUETA_WA.search(tramo))
        limpio = re.sub(r"\([^)]*[A-Za-z][^)]*\)", " ", tramo)
        limpio = re.sub(r"[A-Za-zÁÉÍÓÚáéíóúñÑ:]+", " ", limpio).strip()
        try:
            num = phonenumbers.parse(limpio, "AR")
        except phonenumbers.NumberParseException:
            continue
        if not phonenumbers.is_valid_number(num):
            continue
        if not marcado and phonenumbers.number_type(num) != phonenumbers.PhoneNumberType.MOBILE:
            continue
        e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        if marcado:
            return e164
        celulares.append(e164)
    return celulares[0] if celulares else ""


def datos(df: pd.DataFrame, entrega: pd.DataFrame | None = None) -> list[dict]:
    df = df.fillna("").copy()
    for col in ("localidad", "categoria", "puntaje", "contacto_nombre", "contacto_email", "contacto_telefono", "alerta"):
        if col not in df.columns:
            df[col] = ""
    df["carril"] = df.apply(carril, axis=1)
    df["id"] = [id_empresa(r, l) for r, l in zip(df["razon_social"], df["localidad"])]
    df["tel_e164"] = df["contacto_telefono"].map(telefono_e164)
    df["wa_e164"] = df["contacto_telefono"].map(whatsapp_e164)
    df["provincia"] = ""
    if entrega is not None and len(entrega):
        e = entrega.fillna("")
        mapa = dict(zip(e["razon_social"].map(nombre_normalizado), e.get("provincia", "")))
        df["provincia"] = df["razon_social"].map(nombre_normalizado).map(mapa).fillna("")
    df["_p"] = pd.to_numeric(df.get("puntaje", 0), errors="coerce").fillna(0)
    df["_c"] = df["categoria"].map(_ORDEN_CAT).fillna(3)
    df["_r"] = df["carril"].map(_ORDEN_CARRIL).fillna(4)
    df = df.sort_values(["_c", "_r", "_p", "razon_social"], ascending=[True, True, False, True])
    campos = ["id", "razon_social", "nombre_corto", "localidad", "provincia", "categoria", "puntaje", "rubro",
              "rubro_coi", "plan_sugerido", "web", "madurez_digital", "contacto_nombre", "contacto_cargo",
              "contacto_email", "contacto_telefono", "tel_e164", "wa_e164", "otros_contactos", "empleados_aprox", "senales",
              "dato", "alerta", "nota", "borrador", "fuente_enriquecimiento", "fecha_revision", "carril"]
    return [{c: str(f.get(c, "")) for c in campos} for _, f in df.iterrows()]


def generar(csv: Path, salida: Path, titulo: str = "Prospectos COI", entrega_csv: Path | None = None) -> Path:
    df = pd.read_csv(csv, sep=";", dtype=str)
    entrega = pd.read_csv(entrega_csv, sep=";", dtype=str) if entrega_csv and Path(entrega_csv).exists() else None
    plantilla = (Path(__file__).parent / "tablero.html").read_text(encoding="utf-8")
    seguro = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")  # noqa: E731
    pagina = (plantilla.replace("__TITULO__", html.escape(titulo))
              .replace("__ESTADOS__", seguro([{"clave": c, "etiqueta": e, "grupo": g} for c, e, g in ESTADOS]))
              .replace("__DATOS__", seguro(datos(df, entrega))))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(pagina, encoding="utf-8")
    return salida
