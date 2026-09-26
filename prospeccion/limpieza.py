"""Carga, normalización y deduplicación de listas de empresas."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import phonenumbers
from email_validator import EmailNotValidError, validate_email

CAMPOS = [
    "razon_social", "nombre_fantasia", "cuit", "rubro", "localidad", "provincia", "pais", "web",
    "empleados", "contacto_nombre", "contacto_cargo", "email", "email_estado", "telefono",
    "senales", "fuente",
]

_SUFIJOS_SOCIETARIOS = r"\b(s\.?\s?a\.?\s?s?|s\.?\s?r\.?\s?l|s\.?\s?a\.?\s?u|s\.?\s?h|s\.?\s?c\.?\s?a|sociedad anonima|ltda?|inc|llc)\b\.?"


def clave(texto) -> str:
    """Minúsculas, sin acentos, espacios simples: para comparar textos y nombres de columnas."""
    if texto is None or (not isinstance(texto, str) and pd.isna(texto)):
        return ""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.strip().lower())


def _clave_columna(texto: str) -> str:
    return re.sub(r"[\s\-]+", "_", clave(texto))


def vacio(valor) -> bool:
    return valor is None or (not isinstance(valor, str) and pd.isna(valor)) or not str(valor).strip()


def cargar(ruta: str | Path) -> pd.DataFrame:
    """Lee CSV (detecta separador) o Excel y devuelve todo como texto."""
    ruta = Path(ruta)
    if ruta.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(ruta, dtype=str)
    return pd.read_csv(ruta, dtype=str, sep=None, engine="python", encoding_errors="replace")


def mapear_columnas(df: pd.DataFrame, alias: dict[str, list[str]]) -> pd.DataFrame:
    """Renombra columnas a los campos estándar; conserva las demás tal cual."""
    lookup = {_clave_columna(a): campo for campo, nombres in alias.items() for a in nombres}
    renombres = {}
    for col in df.columns:
        campo = lookup.get(_clave_columna(col))
        if campo and campo not in renombres.values():
            renombres[col] = campo
    df = df.rename(columns=renombres)
    for campo in CAMPOS:
        if campo not in df.columns:
            df[campo] = pd.NA
    return df


def normalizar_cuit(valor) -> str | None:
    """Devuelve el CUIT como XX-XXXXXXXX-X si el dígito verificador es correcto."""
    if vacio(valor):
        return None
    d = re.sub(r"\D", "", str(valor))
    if len(d) != 11:
        return None
    suma = sum(int(a) * b for a, b in zip(d[:10], [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]))
    verificador = 11 - suma % 11
    verificador = {11: 0, 10: 9}.get(verificador, verificador)
    if verificador != int(d[10]):
        return None
    return f"{d[:2]}-{d[2:10]}-{d[10]}"


def normalizar_telefono(valor, pais: str) -> str | None:
    """Devuelve el teléfono en formato E.164 o None si no es válido."""
    if vacio(valor):
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
    if vacio(valor):
        return None
    try:
        return validate_email(str(valor).strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


def dominio_web(valor) -> str | None:
    """'https://www.Empresa.com.ar/obras' -> 'empresa.com.ar'."""
    if vacio(valor):
        return None
    texto = str(valor).strip().lower()
    texto = re.sub(r"^[a-z]+://", "", texto).split("/")[0].split("?")[0]
    texto = texto.removeprefix("www.")
    return texto if "." in texto and " " not in texto else None


def a_numero(valor) -> float | None:
    """Convierte '1.200', '80k', '10-20', '~50' a número (en rangos toma el punto medio)."""
    if vacio(valor):
        return None
    texto = clave(valor)
    # "más de 20", "40 aprox.", "+500", "hasta 50": se toma el número indicado
    texto = re.sub(r"\b(mas de|menos de|hasta|aprox\.?|aproximadamente|cerca de|unos|empleados)\b", " ", texto)
    texto = texto.replace(" ", "").strip(".").lstrip("~+><")
    rango = re.fullmatch(r"(\d+)[-a](\d+)", texto)
    if rango:
        return (float(rango.group(1)) + float(rango.group(2))) / 2
    mult = 1
    if texto.endswith("k"):
        mult, texto = 1_000, texto[:-1]
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", texto):
        texto = re.sub(r"[.,]", "", texto)
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto) * mult
    except ValueError:
        return None


def nombre_normalizado(valor) -> str:
    """Razón social sin sufijo societario ni puntuación, para deduplicar."""
    texto = re.sub(_SUFIJOS_SOCIETARIOS, " ", clave(valor))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def limpiar(df: pd.DataFrame, pais: str) -> pd.DataFrame:
    df = df.copy()
    for col in ("razon_social", "nombre_fantasia", "rubro", "localidad", "provincia", "pais",
                "contacto_nombre", "contacto_cargo", "senales", "fuente", "email_estado"):
        df[col] = df[col].apply(lambda v: pd.NA if vacio(v) else re.sub(r"\s+", " ", str(v)).strip())
    df["contacto_nombre"] = df["contacto_nombre"].apply(lambda v: v.title() if isinstance(v, str) else v)
    df["cuit"] = df["cuit"].apply(normalizar_cuit)
    df["telefono"] = df["telefono"].apply(lambda v: normalizar_telefono(v, pais))
    df["email"] = df["email"].apply(normalizar_email)
    df["web"] = df["web"].apply(dominio_web)
    df["empleados"] = df["empleados"].apply(a_numero)
    sin_identidad = df[["razon_social", "nombre_fantasia", "cuit", "web"]].isna().all(axis=1)
    return df[~sin_identidad].reset_index(drop=True)


def deduplicar(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Une filas con el mismo CUIT, el mismo dominio web o el mismo nombre normalizado + localidad
    (brief, sección 1). Conserva la fila más completa, rellena huecos con las demás y junta las fuentes.
    """
    df = df.copy()
    df["_completitud"] = df[CAMPOS].notna().sum(axis=1)
    if "_confianza" not in df.columns:
        df["_confianza"] = 0
    # Primero la fuente más confiable (verificación > enriquecimiento > cartera), después la más completa
    df["_confianza"] = df["_confianza"].fillna(0)
    df = df.sort_values(["_confianza", "_completitud"], ascending=False, kind="stable").reset_index(drop=True)

    padre = list(range(len(df)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[max(ra, rb)] = min(ra, rb)

    nombre_loc = [
        f"{nombre_normalizado(r.razon_social if not vacio(r.razon_social) else r.nombre_fantasia)}|{clave(r.localidad)}"
        for r in df.itertuples()
    ]
    claves = {
        "cuit": df["cuit"].tolist(),
        "web": df["web"].tolist(),
        "nombre_loc": [k if not k.startswith("|") else None for k in nombre_loc],
    }
    for valores in claves.values():
        vistos: dict[str, int] = {}
        for i, v in enumerate(valores):
            if not vacio(v):
                if v in vistos:
                    unir(vistos[v], i)
                else:
                    vistos[v] = i

    df["_grupo"] = [raiz(i) for i in range(len(df))]
    fuentes = df.groupby("_grupo")["fuente"].apply(
        lambda s: " + ".join(dict.fromkeys(str(x) for x in s if not vacio(x))) or pd.NA)
    resultado = df.groupby("_grupo", sort=True).first()
    resultado["fuente"] = fuentes
    resultado = resultado.reset_index(drop=True).drop(columns=["_completitud", "_confianza"])
    return resultado, len(df) - len(resultado)


def descartar_emails_compartidos(df: pd.DataFrame, maximo: int) -> tuple[pd.DataFrame, int]:
    """Vacía emails que aparecen en `maximo` o más empresas distintas: son comodines de carga, no contactos."""
    df = df.copy()
    empresas = df.assign(_n=df["razon_social"].map(nombre_normalizado)).groupby("email")["_n"].nunique()
    comodines = set(empresas[empresas >= maximo].index)
    mascara = df["email"].isin(comodines)
    df.loc[mascara, "email"] = pd.NA
    return df, int(mascara.sum())
