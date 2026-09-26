"""Borradores de primer contacto (brief, sección 9): ángulo, WhatsApp/email y guion de llamada."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .limpieza import clave, nombre_normalizado, vacio


def nombre_corto(fila: pd.Series) -> str:
    """Nombre para el saludo: fantasía o razón social sin sufijo societario, sin MAYÚSCULAS sostenidas."""
    base = fila.get("nombre_fantasia") if not vacio(fila.get("nombre_fantasia")) else fila.get("razon_social")
    if vacio(base):
        return "tu empresa"
    texto = re.sub(r"[\s,]*\b(s\.?\s?a\.?\s?i\.?\s?c\.?\w*|s\.?\s?r\.?\s?l\.?|s\.?\s?a\.?\s?s\.?|s\.?\s?a\.?|sociedad an[oó]nima|sociedad de responsabilidad limitada)\s*$",
                   "", str(base).strip(), flags=re.IGNORECASE).strip(" .,")
    return texto.title() if texto.isupper() else texto


def saludo_nombre(fila: pd.Series, genericos) -> str:
    """Primer nombre del contacto solo si el saludo le llega a esa persona.

    No se saluda por nombre si el "contacto" es la propia empresa, ni si el email es personal
    de otra persona (el nombre y el email pueden venir de fuentes distintas).
    """
    nombre = fila.get("contacto_nombre")
    if vacio(nombre):
        return ""
    if nombre_normalizado(nombre) in (nombre_normalizado(fila.get("razon_social")), nombre_normalizado(fila.get("nombre_fantasia"))):
        return ""
    partes = [p for p in clave(nombre).replace(".", " ").split() if len(p) > 2]
    email = fila.get("email")
    if not vacio(email):
        local = clave(str(email).split("@")[0])
        es_generico = any(local.startswith(g) for g in genericos)
        if not es_generico and not any(p in local for p in partes):
            return ""
    return partes[0].capitalize() if partes else ""


def _entorno(dir_plantillas: str | Path) -> Environment:
    return Environment(loader=FileSystemLoader(str(dir_plantillas)), undefined=StrictUndefined,
                       trim_blocks=True, lstrip_blocks=True)


def _contexto(fila: pd.Series, config: dict) -> dict:
    ctx = {k: ("" if vacio(v) else v) for k, v in fila.items() if isinstance(k, str)}
    ctx["primer_nombre"] = saludo_nombre(fila, config.get("emails_genericos", []))
    ctx["empresa"] = nombre_corto(fila)
    ctx["frase_rubro"] = fila.get("_frase") or config.get("industrial_generico", {}).get("frase", "es una empresa industrial")
    ctx["rubro_texto"] = (ctx.get("rubro_coi") or ctx.get("rubro") or "la industria").split(" (")[0].lower()
    ctx["dolor"] = fila.get("_dolor") or config.get("industrial_generico", {}).get("dolor", "")
    ctx["solucion"] = fila.get("_solucion") or config.get("industrial_generico", {}).get("solucion", "")
    hechos = [h for h in str(fila.get("_hechos") or "").split(",") if h]
    frases = config.get("hechos", {})
    ctx["dato"] = " y ".join(frases[h] for h in hechos[:2] if h in frases)
    ctx["asunto"] = "margen real y cobranzas en un solo lugar"
    ctx.update(config.get("oferta", {}))
    return ctx


def enlace_whatsapp(telefono: str, texto: str) -> str:
    return f"https://wa.me/{telefono.lstrip('+')}?text={quote(texto)}"


def angulo(ctx: dict) -> str:
    """Resumen de una línea para la columna angulo_primer_contacto."""
    base = f"{ctx['dato']} → " if ctx["dato"] else ""
    return f"{base}{ctx['dolor']}"


def generar(df: pd.DataFrame, dir_plantillas: str | Path, config: dict) -> pd.DataFrame:
    """Completa angulo_primer_contacto y agrega borradores solo para categorías A y B."""
    env = _entorno(dir_plantillas)
    wa, em, ll = (env.get_template(n) for n in ("whatsapp.j2", "email.j2", "llamada.j2"))
    filas = []
    for _, fila in df.iterrows():
        if fila["categoria"] not in ("A", "B"):
            filas.append({"angulo_primer_contacto": pd.NA, "borrador": pd.NA, "email_asunto": pd.NA,
                          "enlace_whatsapp": pd.NA, "guion_llamada": pd.NA})
            continue
        ctx = _contexto(fila, config)
        texto = wa.render(**ctx).strip()
        asunto = em.render(**ctx).strip().split("\n", 1)[0].removeprefix("Asunto:").strip()
        filas.append({
            "angulo_primer_contacto": angulo(ctx),
            "borrador": texto,
            "email_asunto": asunto,
            "enlace_whatsapp": enlace_whatsapp(fila["telefono"], texto) if not vacio(fila["telefono"]) else pd.NA,
            "guion_llamada": ll.render(**ctx).strip() if not vacio(fila["telefono"]) else pd.NA,
        })
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(filas)], axis=1)
