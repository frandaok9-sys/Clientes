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
    texto = re.sub(r"[\s,]*\b(s\.?\s?a\.?\s?i\.?\s?c\.?\w*|s\.?\s?r\.?\s?l\.?|s\.?\s?a\.?\s?s\.?|s\.?\s?a\.?|soc\.?\s+resp\.?\s+ltda\.?|sociedad an[oó]nima|sociedad de responsabilidad limitada)\s*$",
                   "", str(base).strip(), flags=re.IGNORECASE).strip(" .,")
    texto = texto.title() if texto.isupper() else texto
    # Siglas sin vocales vuelven a mayúscula: «Metalurgicas Mg» → «Metalurgicas MG»
    texto = re.sub(r"\b([B-DF-HJ-NP-TV-Z][b-df-hj-np-tv-z]{1,2})\b", lambda m: m.group(1).upper(), texto)
    # «Tecnicas Avanzadas De Ingenieria» → «Tecnicas Avanzadas de Ingenieria»: conectores en minúscula salvo al inicio
    return re.sub(r"(?<=\s)(De|Del|Y|E|La|Las|Los|El|En|Para|Por)(?=\s)", lambda m: m.group(1).lower(), texto)


def decisor_dudoso(cargo) -> bool:
    """El dato del decisor no alcanza para saludarlo por nombre: sin confirmar o anterior a 2020."""
    if vacio(cargo):
        return False
    texto = clave(cargo)
    if any(m in texto for m in ("sin confirmar", "verificar", "sin precisar")):
        return True
    anios = [int(a) for a in re.findall(r"\b(19\d{2}|20\d{2})\b", str(cargo))]
    return bool(anios) and max(anios) < 2020


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
    if decisor_dudoso(fila.get("contacto_cargo")):
        return ""
    partes = [p for p in clave(nombre).replace(".", " ").split() if len(p) > 2]
    email = fila.get("email")
    if not vacio(email):
        local = clave(str(email).split("@")[0])
        es_generico = any(local.startswith(g) for g in genericos)
        if not es_generico and not any(p in local for p in partes):
            return ""
    if not partes:
        return ""
    # Devuelve la palabra original (con acentos), no la normalizada
    for palabra in str(nombre).replace(".", " ").split():
        if clave(palabra) == partes[0]:
            return palabra.capitalize()
    return partes[0].capitalize()


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
    ctx["solucion_generica"] = config.get("industrial_generico", {}).get("solucion", "")
    ctx["solucion"] = fila.get("_solucion") or ctx["solucion_generica"]
    hechos = [h for h in str(fila.get("_hechos") or "").split(",") if h]
    frases = config.get("hechos", {})
    ctx["dato"] = " y ".join(frases[h] for h in hechos[:2] if h in frases)
    ctx["dato1"] = next((frases[h] for h in hechos if h in frases), "")  # el email lleva un solo dato
    ctx["asunto"] = fila.get("_asunto") or config.get("industrial_generico", {}).get("asunto", "toda tu empresa en tiempo real")
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
            filas.append({"angulo_primer_contacto": pd.NA, "borrador": pd.NA, "email_asunto": pd.NA, "email_cuerpo": pd.NA,
                          "enlace_whatsapp": pd.NA, "guion_llamada": pd.NA})
            continue
        ctx = _contexto(fila, config)
        texto = wa.render(**ctx).strip()
        cabecera, cuerpo = em.render(**ctx).strip().split("\n", 1)
        asunto = cabecera.removeprefix("Asunto:").strip()
        filas.append({
            "angulo_primer_contacto": angulo(ctx),
            "borrador": texto,
            "email_asunto": asunto,
            "email_cuerpo": cuerpo.strip(),
            "enlace_whatsapp": enlace_whatsapp(fila["telefono"], texto) if not vacio(fila["telefono"]) else pd.NA,
            "guion_llamada": ll.render(**ctx).strip() if not vacio(fila["telefono"]) else pd.NA,
        })
    nuevas = pd.DataFrame(filas)
    df = df.drop(columns=[c for c in nuevas.columns if c in df.columns])
    return pd.concat([df.reset_index(drop=True), nuevas], axis=1)
