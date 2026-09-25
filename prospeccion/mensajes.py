"""Generación de mensajes personalizados, enlaces de WhatsApp y guiones de llamada."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _entorno(dir_plantillas: str | Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(dir_plantillas)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _contexto(fila: pd.Series, extra: dict) -> dict:
    ctx = {k: ("" if pd.isna(v) else v) for k, v in fila.items()}
    nombre = str(ctx.get("nombre") or "").strip()
    ctx["primer_nombre"] = nombre.split(" ")[0] if nombre else ""
    ctx.update(extra)
    return ctx


def enlace_whatsapp(telefono: str, texto: str) -> str:
    return f"https://wa.me/{telefono.lstrip('+')}?text={quote(texto)}"


def generar(df: pd.DataFrame, dir_plantillas: str | Path, extra: dict) -> pd.DataFrame:
    """Añade columnas: mensaje_whatsapp, enlace_whatsapp, email_asunto, email_cuerpo, guion_llamada."""
    env = _entorno(dir_plantillas)
    wa = env.get_template("whatsapp.j2")
    em = env.get_template("email.j2")
    ll = env.get_template("llamada.j2")

    filas = []
    for _, fila in df.iterrows():
        ctx = _contexto(fila, extra)
        texto_wa = wa.render(**ctx).strip()
        asunto, _, cuerpo = em.render(**ctx).strip().partition("\n")
        filas.append({
            "mensaje_whatsapp": texto_wa,
            "enlace_whatsapp": enlace_whatsapp(fila["telefono"], texto_wa) if pd.notna(fila["telefono"]) else "",
            "email_asunto": asunto.removeprefix("Asunto:").strip(),
            "email_cuerpo": cuerpo.strip(),
            "guion_llamada": ll.render(**ctx).strip(),
        })
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(filas)], axis=1)
