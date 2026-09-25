"""Carga, normalización y deduplicación de listas de clientes."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import phonenumbers
from email_validator import EmailNotValidError, validate_email
from rapidfuzz import fuzz

CAMPOS = [
    "nombre", "empresa", "telefono", "email", "sector", "ciudad",
    "empleados", "facturacion", "web", "ultima_compra", "notas",
]


def _clave(texto: str) -> str:
    """Minúsculas, sin acentos ni espacios extra: para comparar nombres de columnas y textos."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[\s\-]+", "_", texto.strip().lower())


def cargar(ruta: str | Path) -> pd.DataFrame:
    """Lee CSV (detecta separador) o Excel y devuelve todo como texto."""
    ruta = Path(ruta)
    if ruta.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(ruta, dtype=str)
    return pd.read_csv(ruta, dtype=str, sep=None, engine="python", encoding_errors="replace")


def mapear_columnas(df: pd.DataFrame, alias: dict[str, list[str]]) -> pd.DataFrame:
    """Renombra columnas del archivo a los campos estándar; conserva las demás tal cual."""
    lookup = {_clave(a): campo for campo, nombres in alias.items() for a in nombres}
    renombres = {}
    for col in df.columns:
        campo = lookup.get(_clave(col))
        if campo and campo not in renombres.values():
            renombres[col] = campo
    df = df.rename(columns=renombres)
    for campo in CAMPOS:
        if campo not in df.columns:
            df[campo] = pd.NA
    return df


def normalizar_telefono(valor, pais: str) -> str | None:
    """Devuelve el teléfono en formato E.164 (+34600111222) o None si no es válido."""
    if valor is None or pd.isna(valor) or not str(valor).strip():
        return None
    texto = str(valor).strip()
    if texto.startswith("00"):
        texto = "+" + texto[2:]
    try:
        num = phonenumbers.parse(texto, pais)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def normalizar_email(valor) -> str | None:
    if valor is None or pd.isna(valor) or not str(valor).strip():
        return None
    try:
        return validate_email(str(valor).strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


def a_numero(valor) -> float | None:
    """Convierte '1.200', '1,5M', '250k', '10-20' a número (en rangos toma el punto medio)."""
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip().lower().replace("€", "").replace("$", "").replace(" ", "")
    if not texto:
        return None
    rango = re.fullmatch(r"(\d+)[-a](\d+)", texto)
    if rango:
        return (float(rango.group(1)) + float(rango.group(2))) / 2
    mult = 1
    if texto.endswith(("m", "mm")):
        mult, texto = 1_000_000, texto.rstrip("m")
    elif texto.endswith("k"):
        mult, texto = 1_000, texto[:-1]
    # Separadores: "1.200.000" / "1,200,000" miles; "1,5" / "1.5" decimal
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", texto):
        texto = re.sub(r"[.,]", "", texto)
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto) * mult
    except ValueError:
        return None


def limpiar(df: pd.DataFrame, pais: str) -> pd.DataFrame:
    df = df.copy()
    for col in ("nombre", "empresa", "sector", "ciudad", "web", "notas"):
        df[col] = df[col].apply(
            lambda v: re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) and str(v).strip() else pd.NA
        )
    df["nombre"] = df["nombre"].apply(lambda v: v.title() if pd.notna(v) else v)
    df["telefono_original"] = df["telefono"]
    df["telefono"] = df["telefono"].apply(lambda v: normalizar_telefono(v, pais))
    df["email"] = df["email"].apply(normalizar_email)
    df["empleados"] = df["empleados"].apply(a_numero)
    df["facturacion"] = df["facturacion"].apply(a_numero)
    # Descarta filas sin ninguna forma de identificar/contactar
    vacias = df[["nombre", "empresa", "telefono", "email"]].isna().all(axis=1)
    return df[~vacias].reset_index(drop=True)


def deduplicar(df: pd.DataFrame, umbral_similitud: int = 92) -> tuple[pd.DataFrame, int]:
    """Elimina duplicados por teléfono, email o nombre+empresa muy similares.

    Se queda con la fila con más datos rellenos. Devuelve (df, n_eliminados).
    """
    df = df.copy()
    df["_completitud"] = df[CAMPOS].notna().sum(axis=1)
    df = df.sort_values("_completitud", ascending=False).reset_index(drop=True)

    grupo = list(range(len(df)))

    def raiz(i):
        while grupo[i] != i:
            grupo[i] = grupo[grupo[i]]
            i = grupo[i]
        return i

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            grupo[max(ra, rb)] = min(ra, rb)

    for campo in ("telefono", "email"):
        vistos: dict[str, int] = {}
        for i, v in df[campo].items():
            if pd.notna(v):
                if v in vistos:
                    unir(vistos[v], i)
                else:
                    vistos[v] = i

    # Coincidencia difusa de nombre+empresa, agrupando por inicial para no comparar todo con todo
    etiqueta = (df["nombre"].fillna("") + " | " + df["empresa"].fillna("")).map(_clave)
    bloques: dict[str, list[int]] = {}
    for i, e in etiqueta.items():
        if len(e) > 5:
            bloques.setdefault(e[:2], []).append(i)
    for indices in bloques.values():
        for x in range(len(indices)):
            for y in range(x + 1, len(indices)):
                a, b = indices[x], indices[y]
                if fuzz.token_sort_ratio(etiqueta[a], etiqueta[b]) >= umbral_similitud:
                    unir(a, b)

    df["_grupo"] = [raiz(i) for i in range(len(df))]
    # Completa huecos del registro principal con datos de sus duplicados
    resultado = df.groupby("_grupo", sort=True).first().reset_index(drop=True)
    eliminados = len(df) - len(resultado)
    return resultado.drop(columns=["_completitud"]), eliminados
