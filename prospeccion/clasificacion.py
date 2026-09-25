"""Puntuación (lead scoring) y segmentación A/B/C según config.yaml."""

from __future__ import annotations

import pandas as pd

from .limpieza import _clave


def _contiene(valor, palabras: list[str]) -> bool:
    if valor is None or pd.isna(valor) or not palabras:
        return False
    texto = _clave(valor)
    return any(_clave(p) in texto for p in palabras)


def _por_rango(valor, rangos) -> int:
    if valor is None or pd.isna(valor):
        return 0
    for minimo, maximo, puntos in rangos:
        if minimo <= valor <= maximo:
            return puntos
    return 0


def puntuar_fila(fila: pd.Series, reglas: dict) -> tuple[int, list[str]]:
    puntos, motivos = 0, []

    def sumar(p, motivo):
        nonlocal puntos
        if p:
            puntos += p
            motivos.append(f"{motivo} (+{p})")

    s = reglas.get("sectores_objetivo", {})
    if _contiene(fila.get("sector"), s.get("valores", [])):
        sumar(s.get("puntos", 0), "sector objetivo")
    sumar(_por_rango(fila.get("empleados"), reglas.get("empleados", [])), "tamaño")
    sumar(_por_rango(fila.get("facturacion"), reglas.get("facturacion", [])), "facturación")
    if pd.notna(fila.get("telefono")):
        sumar(reglas.get("tiene_telefono_valido", 0), "teléfono válido")
    if pd.notna(fila.get("email")):
        sumar(reglas.get("tiene_email_valido", 0), "email válido")
    if pd.notna(fila.get("web")):
        sumar(reglas.get("tiene_web", 0), "tiene web")
    z = reglas.get("zonas_prioritarias", {})
    if _contiene(fila.get("ciudad"), z.get("valores", [])):
        sumar(z.get("puntos", 0), "zona prioritaria")
    k = reglas.get("palabras_clave_interes", {})
    if _contiene(fila.get("notas"), k.get("valores", [])):
        sumar(k.get("puntos", 0), "señal de interés")
    return min(puntos, 100), motivos


def segmento(puntos: int, umbrales: dict) -> str:
    if puntos >= umbrales.get("A", 60):
        return "A"
    if puntos >= umbrales.get("B", 35):
        return "B"
    return "C"


def canal_para(seg: str, fila: pd.Series, canales: dict) -> str:
    """Canal recomendado, degradando si falta el dato de contacto necesario."""
    canal = canales.get(seg, "email")
    tiene_tel = pd.notna(fila.get("telefono"))
    tiene_mail = pd.notna(fila.get("email"))
    if canal in ("llamada", "whatsapp") and not tiene_tel:
        canal = "email" if tiene_mail else "sin_contacto"
    elif canal == "email" and not tiene_mail:
        canal = "whatsapp" if tiene_tel else "sin_contacto"
    return canal


def clasificar(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = df.copy()
    resultados = df.apply(lambda f: puntuar_fila(f, config.get("puntuacion", {})), axis=1)
    df["puntuacion"] = [r[0] for r in resultados]
    df["motivos"] = ["; ".join(r[1]) for r in resultados]
    df["segmento"] = df["puntuacion"].apply(lambda p: segmento(p, config.get("segmentos", {})))
    df["canal"] = df.apply(lambda f: canal_para(f["segmento"], f, config.get("canal", {})), axis=1)
    if "estado" not in df.columns:
        df["estado"] = "pendiente"
    return df.sort_values(["segmento", "puntuacion"], ascending=[True, False]).reset_index(drop=True)
