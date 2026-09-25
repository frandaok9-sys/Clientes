"""Importadores de carteras con formato propio → CSV con las columnas estándar del kit.

- RAI: exportación de CRM (Nombre completo, Teléfono, Correo, Vendedor, Ciudad, País, Estado).
- AG-360: planilla por zonas, sin encabezados (nombre, CUIT, código, localidad, contacto, email, tel1, tel2).
- PDF de zonas: listados de clientes (Id, Cliente, Región, Ciudad, Dirección, Estado...).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .limpieza import clave, vacio

# Marcas internas de estado que a veces vienen pegadas al nombre y no deben llegar a ningún borrador
_MARCAS_INTERNAS = re.compile(r"\b(prejudicial|judicial|moroso|incobrable|no usar)\b", re.IGNORECASE)


def _limpiar_nombre(valor):
    if vacio(valor):
        return pd.NA
    texto = _MARCAS_INTERNAS.sub(" ", str(valor))
    return re.sub(r"\s+", " ", texto).strip() or pd.NA


def _persona_apellido_nombre(nombre: str) -> str:
    """'Gomez, Maria Julia' -> 'Maria Julia Gomez'."""
    if isinstance(nombre, str) and nombre.count(",") == 1:
        ap, no = (p.strip() for p in nombre.split(","))
        if ap and no:
            return f"{no} {ap}"
    return nombre


def leer_rai(ruta: str | Path) -> pd.DataFrame:
    df = pd.read_excel(ruta, dtype=str)
    col = {clave(c): c for c in df.columns}
    nombre = df[col["nombre completo"]].map(_limpiar_nombre)
    email = df[col["correo electronico"]]
    # Filas cuyo "nombre" es en realidad un email: se conserva el email, sin razón social
    es_email = nombre.fillna("").str.contains("@")
    email = email.where(~es_email | email.notna(), nombre)
    nombre = nombre.where(~es_email)
    out = pd.DataFrame({
        "razon_social": nombre,
        "telefono": df[col["telefono"]],
        "email": email,
        "localidad": df[col["ciudad"]],
        "pais": df[col["pais"]],
        "vendedor_origen": df[col["vendedor"]],
        "estado_origen": df[col["estado de empresas"]],
    })
    out["persona_fisica"] = out["razon_social"].fillna("").str.fullmatch(r"[^,]+,[^,]+")
    out["razon_social"] = out["razon_social"].map(_persona_apellido_nombre)
    out["fuente"] = "Cartera RAI"
    return out


def leer_ag360(ruta: str | Path) -> pd.DataFrame:
    marcos = []
    for hoja in pd.ExcelFile(ruta).sheet_names:
        d = pd.read_excel(ruta, sheet_name=hoja, header=None, dtype=str)
        d = d[~d.apply(lambda f: f.astype(str).str.contains("CRM AG-360").any(), axis=1)]
        # La columna del CUIT es la que tiene más valores de 11 dígitos; el nombre está a su izquierda
        cuit_col = max(range(d.shape[1]), key=lambda i: d.iloc[:, i].fillna("").str.fullmatch(r"\d{11}").sum())
        if cuit_col == 0 or d.shape[1] < cuit_col + 7:
            continue
        d = d.iloc[:, cuit_col - 1:cuit_col + 7].dropna(axis=0, how="all")
        d.columns = ["razon_social", "cuit", "codigo_origen", "localidad", "contacto_nombre", "email", "tel1", "tel2"]
        d["telefono"] = d["tel2"].where(d["tel2"].fillna("").str.len() >= d["tel1"].fillna("").str.len(), d["tel1"])
        d["zona_origen"] = hoja
        marcos.append(d.drop(columns=["tel1", "tel2"]))
    out = pd.concat(marcos, ignore_index=True)
    out["razon_social"] = out["razon_social"].map(_limpiar_nombre)
    out["contacto_nombre"] = out["contacto_nombre"].map(_limpiar_nombre)
    out["cuit"] = out["cuit"].where(out["cuit"] != "0")
    out["persona_fisica"] = out["cuit"].fillna("").str.match(r"^(20|23|24|27)")
    out["pais"] = "Argentina"
    out["fuente"] = "Cartera AG-360 (F. Dabbene)"
    return out


# --- PDF de zonas -----------------------------------------------------------------------------

_COLUMNAS_PDF = {
    "Id": "id_origen", "Cliente": "razon_social", "Empresa": "nombre_fantasia", "Región": "provincia",
    "Ciudad": "localidad", "Dirección": "direccion", "Condición": "condicion_pago", "Estado": "estado_origen",
    "Usuarios": "usuario_origen",
}


def _celdas(chars, inicios: list[float]) -> list[tuple[float, str]]:
    """Agrupa caracteres (en el orden en que se dibujan) en celdas.

    Los PDF traen texto superpuesto cuando una celda desborda a la siguiente; leer por
    posición mezcla letras. En orden de dibujo, cada celda es una corrida continua.
    """
    corridas, actual, prev = [], None, None
    for c in chars:
        nueva = (
            prev is None
            or c["x0"] < prev["x1"] - 1                                   # salto hacia atrás
            or c["x0"] - prev["x1"] > 12                                   # hueco grande
            or (c["x0"] - prev["x1"] > 0.8 and any(abs(c["x0"] - i) < 2.5 for i in inicios))
        )
        if nueva:
            actual = [c]
            corridas.append(actual)
        else:
            actual.append(c)
        prev = c
    return [(r[0]["x0"], re.sub(r"\s+", " ", "".join(ch["text"] for ch in r)).strip()) for r in corridas]


def leer_pdf_zonas(ruta: str | Path) -> pd.DataFrame:
    import pdfplumber

    filas, columnas, inicios = [], None, []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            palabras = pagina.extract_words()
            if not palabras:
                continue
            encabezado = [w for w in palabras if w["text"] in _COLUMNAS_PDF and w["top"] < palabras[0]["top"] + 3
                          and palabras[0]["text"] == "Id"]
            if encabezado:  # las páginas siguientes reutilizan las columnas de la última cabecera
                columnas = sorted((w["x0"], _COLUMNAS_PDF[w["text"]]) for w in encabezado)
                inicios = [x for x, _ in columnas]
            if columnas is None:
                continue
            desde = encabezado[0]["bottom"] + 1 if encabezado else 0
            lineas: dict[int, list] = {}
            for c in pagina.chars:
                if c["top"] > desde:
                    lineas.setdefault(round(c["top"]), []).append(c)
            for top in sorted(lineas):
                fila: dict[str, str] = {}
                for x, texto in _celdas(lineas[top], inicios):
                    nombre = [n for xi, n in columnas if xi <= x + 2.5]
                    if nombre and texto:
                        fila[nombre[-1]] = (fila.get(nombre[-1], "") + " " + texto).strip()
                if fila.get("id_origen", "").isdigit():
                    filas.append(fila)
                elif filas and fila:  # continuación de una celda en varias líneas
                    for k, v in fila.items():
                        filas[-1][k] = (filas[-1].get(k, "") + " " + v).strip()
    out = pd.DataFrame(filas)
    for campo in ("razon_social", "nombre_fantasia", "provincia", "localidad"):
        if campo not in out.columns:
            out[campo] = pd.NA
    out["razon_social"] = out["razon_social"].map(_limpiar_nombre)
    out["pais"] = "Argentina"
    out["fuente"] = f"Listado {Path(ruta).stem}"
    return out


def importar(ruta: str | Path) -> pd.DataFrame:
    """Detecta el formato por el contenido y devuelve el DataFrame normalizado."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".pdf":
        return leer_pdf_zonas(ruta)
    hojas = pd.ExcelFile(ruta).sheet_names
    primera = pd.read_excel(ruta, sheet_name=hojas[0], nrows=2, dtype=str)
    if any(clave(c) == "nombre completo" for c in primera.columns):
        return leer_rai(ruta)
    return leer_ag360(ruta)


def es_formato_propio(ruta: str | Path, alias: dict[str, list[str]]) -> bool:
    """True si el archivo necesita un importador propio (PDF, RAI o planilla sin encabezados)."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".pdf":
        return True
    if ruta.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
        return False
    columnas = {clave(c).replace(" ", "_") for c in pd.read_excel(ruta, nrows=0).columns}
    if "nombre_completo" in columnas:
        return True
    reconocidas = {clave(a).replace(" ", "_") for campo in ("razon_social", "cuit") for a in alias.get(campo, [])}
    return not columnas & reconocidas
