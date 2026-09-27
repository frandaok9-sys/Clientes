"""Cartera unificada: una fila por empresa con la procedencia de cada dato.

Une la entrega (carteras deduplicadas y calificadas) con lo que trajo la investigación. Separa
siempre el contacto **de origen** (tal como vino en la cartera del vendedor, sin verificar) del
contacto **verificado** (encontrado en una fuente pública, con URL y fecha). Nada se deduce: lo que
no se encontró queda vacío.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import importar, limpieza
from .limpieza import nombre_normalizado, vacio

COLUMNAS = [
    "razon_social", "nombre_corto", "cuit", "localidad", "provincia", "persona_fisica",
    "origen", "origen_detalle",
    "rubro_coi", "rubro_estado", "rubro_detalle",
    "categoria", "puntaje", "motivo_descarte", "estado_investigacion",
    "web", "madurez_digital",
    "contacto_origen_nombre", "contacto_origen_email", "contacto_origen_telefono",
    "decisor_nombre", "decisor_cargo", "email_verificado", "telefono_verificado", "otros_contactos",
    "verificar_no_llame", "empleados_aprox", "alerta", "nota", "fuente_verificacion", "fecha_verificacion",
]
_ORIGEN = re.compile(r"^(Cartera|Listado)\b")
_ORDEN_CAT = {"A": 0, "B": 1, "C": 2, "C - chico": 3, "Descartada": 4}


def _clave(df: pd.DataFrame) -> pd.Series:
    nombre = df["razon_social"].where(df["razon_social"].notna() & (df["razon_social"] != ""), df.get("nombre_fantasia"))
    return nombre.fillna("").map(nombre_normalizado)


def _juntar(valores) -> str:
    return " / ".join(dict.fromkeys(str(v).strip() for v in valores if not vacio(v) and str(v).strip()))


def leer_origen(carpeta: str | Path, alias: dict) -> pd.DataFrame:
    """Contactos y datos tal como vienen en cada cartera, agrupados por empresa (sin verificar)."""
    marcos = []
    for ruta in sorted(Path(carpeta).iterdir()):
        if ruta.suffix.lower() not in {".csv", ".xlsx", ".xls", ".pdf"}:
            continue
        df = importar.importar(ruta) if importar.es_formato_propio(ruta, alias) else limpieza.cargar(ruta)
        df = limpieza.mapear_columnas(df, alias)
        detalle = df.get("vendedor_origen", pd.Series(pd.NA, index=df.index)).fillna("")
        for col, etiqueta in (("zona_origen", ""), ("usuario_origen", "usuario ")):
            if col in df.columns:
                detalle = detalle.where(detalle != "", etiqueta + df[col].fillna(""))
        etiqueta = df["fuente"].fillna(ruta.name).astype(str)
        marcos.append(pd.DataFrame({
            "_k": _clave(df),
            "contacto_origen_nombre": df.get("contacto_nombre"),
            "contacto_origen_email": df.get("email").map(limpieza.normalizar_email) if "email" in df else pd.NA,
            "contacto_origen_telefono": df.get("telefono").map(lambda v: limpieza.normalizar_telefono(v, "AR")) if "telefono" in df else pd.NA,
            "origen_detalle": (etiqueta + ": " + detalle.astype(str)).where(detalle.astype(str) != "", etiqueta),
            "persona_fisica": df.get("persona_fisica", pd.Series(False, index=df.index)).fillna(False).astype(bool),
        }))
    if not marcos:
        return pd.DataFrame(columns=["_k"])
    todo = pd.concat(marcos, ignore_index=True)
    todo = todo[todo["_k"] != ""]
    return todo.groupby("_k").agg(
        contacto_origen_nombre=("contacto_origen_nombre", _juntar),
        contacto_origen_email=("contacto_origen_email", _juntar),
        contacto_origen_telefono=("contacto_origen_telefono", _juntar),
        origen_detalle=("origen_detalle", _juntar),
        persona_fisica=("persona_fisica", "any"),
    ).reset_index()


def leer_verificado(prospectos: pd.DataFrame) -> pd.DataFrame:
    """Lo investigado en fuentes públicas. Un contacto solo cuenta como verificado si la fila trae la URL."""
    p = prospectos.fillna("").copy()
    p["_k"] = _clave(p)
    con_fuente = p["fuente_enriquecimiento"].str.strip() != ""
    out = pd.DataFrame({
        "_k": p["_k"],
        "_loc": p.get("localidad", pd.Series("", index=p.index)).map(limpieza.clave),
        "nombre_corto": p["nombre_corto"],
        "rubro_detalle": p["rubro"],
        "rubro_coi_verificado": p["rubro_coi"],
        "categoria_inv": p["categoria"],
        "puntaje_inv": p["puntaje"],
        "web_inv": p["web"],
        "madurez_inv": p["madurez_digital"],
        "decisor_nombre": p["contacto_nombre"].where(con_fuente, ""),
        "decisor_cargo": p["contacto_cargo"].where(con_fuente, ""),
        "email_verificado": p["contacto_email"].where(con_fuente, ""),
        "telefono_verificado": p["contacto_telefono"].where(con_fuente, ""),
        "otros_contactos": p["otros_contactos"].where(con_fuente, ""),
        "empleados_inv": p["empleados_aprox"],
        "alerta": p["alerta"],
        "nota": p["nota"].where(con_fuente, (p["nota"] + " | contacto sin fuente: no se usa").str.strip(" |")),
        "fuente_verificacion": p["fuente_enriquecimiento"],
        "fecha_verificacion": p["fecha_revision"],
    })
    return out.drop_duplicates("_k")


def leer_rapida(rapida: pd.DataFrame) -> pd.DataFrame:
    """Pasada rápida de rubro: solo qué es la empresa, con URL. No trae contactos."""
    r = rapida.fillna("").copy()
    r["_k"] = _clave(r)
    con_fuente = r["fuente_enriquecimiento"].str.strip() != ""
    out = pd.DataFrame({
        "_k": r["_k"],
        "rubro_rapida": r["rubro"].where(con_fuente, ""),
        "web_rapida": r["web"].where(con_fuente, ""),
        "empleados_rapida": r.get("empleados", pd.Series("", index=r.index)).where(con_fuente, ""),
        "alerta_rapida": r["alerta"],
        "fuente_rapida": r["fuente_enriquecimiento"],
        "fecha_rapida": r.get("fecha_revision", pd.Series("", index=r.index)),
    })
    return out.drop_duplicates("_k")


def leer_descartadas_en_investigacion(tandas: str | Path, investigadas: set[str]) -> dict[str, str]:
    """Empresas que un agente investigó y no entraron a prospectos: quedan con el motivo (su alerta)."""
    motivos: dict[str, str] = {}
    for ruta in sorted(Path(tandas).glob("[tr]*_out*.csv")):
        try:
            d = pd.read_csv(ruta, sep=";", dtype=str).fillna("")
        except Exception:
            continue
        if "razon_social" not in d.columns:
            continue
        for _, f in d.iterrows():
            k = nombre_normalizado(f["razon_social"])
            if k and k not in investigadas:
                motivos.setdefault(k, f.get("alerta", "") or "sin datos suficientes")
    return motivos


def unificar(entrega: pd.DataFrame, origen: pd.DataFrame, verificado: pd.DataFrame,
             descartadas: dict[str, str] | None = None, rapida: pd.DataFrame | None = None) -> pd.DataFrame:
    e = entrega.fillna("").copy()
    e["_k"] = _clave(e)
    df = e.merge(origen, on="_k", how="left").merge(verificado, on="_k", how="left")
    if rapida is None or rapida.empty:
        rapida = pd.DataFrame(columns=["_k", "rubro_rapida", "web_rapida", "empleados_rapida", "alerta_rapida", "fuente_rapida", "fecha_rapida"])
    df = df.merge(rapida, on="_k", how="left").fillna("")
    for col in ("nombre_corto", "rubro_detalle", "rubro_coi_verificado", "categoria_inv", "puntaje_inv", "web_inv", "madurez_inv",
                "decisor_nombre", "decisor_cargo", "email_verificado", "telefono_verificado", "otros_contactos", "empleados_inv",
                "alerta", "nota", "fuente_verificacion", "fecha_verificacion"):
        if col not in df.columns:
            df[col] = ""
    # Homónimos: si varias filas comparten el nombre, lo verificado va solo a la de la misma localidad
    if "_loc" in df.columns:
        repetidas = df["_k"].duplicated(keep=False)
        otra_loc = repetidas & (df["_loc"] != "") & (df["_loc"] != df["localidad"].map(limpieza.clave))
        df.loc[otra_loc, [c for c in verificado.columns if c not in ("_k", "_loc")]] = ""
    investigada = df["fuente_verificacion"].astype(str) != ""
    df["persona_fisica"] = df["persona_fisica"].map(lambda v: "sí" if v is True else "")
    df["origen"] = df["fuente"].map(lambda s: " + ".join(t for t in str(s).split(" + ") if _ORIGEN.match(t)))
    df["nombre_corto"] = df["nombre_corto"].where(df["nombre_corto"] != "", df["nombre_fantasia"])
    df["rubro_detalle"] = df["rubro_detalle"].where(investigada, "")
    df["rubro_coi"] = df["rubro_coi_verificado"].where(investigada & (df["rubro_coi_verificado"] != ""), df["rubro_coi"])
    pasada = ~investigada & (df["rubro_rapida"] != "")
    df["rubro_detalle"] = df["rubro_detalle"].where(~pasada, df["rubro_rapida"])
    df["web"] = df["web"].where(~(pasada & (df["web_rapida"] != "")), df["web_rapida"])
    df["empleados_aprox"] = df["empleados_aprox"].where(~(pasada & (df["empleados_rapida"] != "")), df["empleados_rapida"])
    df["alerta"] = df["alerta"].where(investigada, df["alerta_rapida"])
    df["fuente_verificacion"] = df["fuente_verificacion"].where(investigada, df["fuente_rapida"])
    df["fecha_verificacion"] = df["fecha_verificacion"].where(investigada, df["fecha_rapida"])
    df["rubro_estado"] = "sin dato"
    df.loc[df["rubro_coi"] != "", "rubro_estado"] = "por nombre (sin verificar)"
    df.loc[pasada, "rubro_estado"] = "verificado (pasada rápida)"
    df.loc[investigada & (df["rubro_detalle"] != ""), "rubro_estado"] = "verificado"
    df["categoria"] = df["categoria_inv"].where(investigada & (df["categoria_inv"] != ""), df["categoria"])
    df["puntaje"] = df["puntaje_inv"].where(investigada & (df["puntaje_inv"] != ""), df["puntaje"])
    df["web"] = df["web_inv"].where(investigada & (df["web_inv"] != ""), df["web"])
    df["empleados_aprox"] = df["empleados_inv"].where(investigada & (df["empleados_inv"] != ""), df["empleados_aprox"])
    df["madurez_digital"] = df["madurez_inv"].where(investigada & (df["madurez_inv"] != ""), df["madurez_digital"])
    df["estado_investigacion"] = "pendiente"
    df.loc[df["categoria"] == "Descartada", "estado_investigacion"] = "descartada por reglas"
    for k, motivo in (descartadas or {}).items():
        sel = (df["_k"] == k) & ~investigada
        df.loc[sel, "estado_investigacion"] = "descartada en investigación"
        df.loc[sel & (df["motivo_descarte"] == ""), "motivo_descarte"] = motivo
    df.loc[pasada & (df["estado_investigacion"] == "pendiente"), "estado_investigacion"] = "rubro confirmado (falta decisor y canal)"
    df.loc[investigada, "estado_investigacion"] = "investigada"
    hay_tel = (df["telefono_verificado"] != "") | (df["contacto_origen_telefono"] != "")
    df["verificar_no_llame"] = hay_tel.map({True: "sí", False: ""})
    df["_orden"] = df["categoria"].map(_ORDEN_CAT).fillna(5)
    df["_inv"] = (~investigada).astype(int)
    df["_p"] = pd.to_numeric(df["puntaje"], errors="coerce").fillna(-1)
    df = df.sort_values(["_inv", "_orden", "_p", "razon_social"], ascending=[True, True, False, True])
    return df[COLUMNAS].reset_index(drop=True)


def resumen_por_rubro(cartera: pd.DataFrame) -> pd.DataFrame:
    c = cartera.copy()
    c["rubro"] = c["rubro_coi"].replace("", "(sin rubro)")
    c["decisor"] = (c["decisor_nombre"] != "").astype(int)
    c["canal_verificado"] = ((c["email_verificado"] != "") | (c["telefono_verificado"] != "")).astype(int)
    c["investigadas"] = (c["estado_investigacion"] == "investigada").astype(int)
    c["por_nombre"] = (c["rubro_estado"] == "por nombre (sin verificar)").astype(int)
    r = c.groupby("rubro").agg(empresas=("razon_social", "size"), rubro_verificado=("investigadas", "sum"),
                               rubro_por_nombre=("por_nombre", "sum"), con_decisor=("decisor", "sum"),
                               con_canal_verificado=("canal_verificado", "sum")).reset_index()
    return r.sort_values("empresas", ascending=False).reset_index(drop=True)


def generar(entrega_csv: Path, prospectos_csv: Path, carteras: Path, tandas: Path, salida_csv: Path,
            salida_xlsx: Path | None, alias: dict) -> pd.DataFrame:
    entrega = pd.read_csv(entrega_csv, sep=";", dtype=str)
    prospectos = pd.read_csv(prospectos_csv, sep=";", dtype=str) if Path(prospectos_csv).exists() else pd.DataFrame(columns=["razon_social"])
    verificado = leer_verificado(prospectos) if len(prospectos) else pd.DataFrame(columns=["_k"])
    descartadas = leer_descartadas_en_investigacion(tandas, set(verificado["_k"])) if Path(tandas).exists() else {}
    ruta_rapida = Path(prospectos_csv).parent / "20260927-rubro-rapido.csv"
    rapida = leer_rapida(pd.read_csv(ruta_rapida, sep=";", dtype=str)) if ruta_rapida.exists() else None
    cartera = unificar(entrega, leer_origen(carteras, alias), verificado, descartadas, rapida)
    salida_csv.parent.mkdir(parents=True, exist_ok=True)
    cartera.to_csv(salida_csv, sep=";", index=False, encoding="utf-8")
    if salida_xlsx:
        with pd.ExcelWriter(salida_xlsx, engine="openpyxl") as xw:
            resumen_por_rubro(cartera).to_excel(xw, sheet_name="Resumen por rubro", index=False)
            cartera[cartera["estado_investigacion"] == "investigada"].to_excel(xw, sheet_name="Investigadas", index=False)
            pendientes = cartera[(cartera["estado_investigacion"] == "pendiente") & (cartera["rubro_coi"] != "")]
            pendientes.to_excel(xw, sheet_name="Pendientes con rubro", index=False)
            cartera.to_excel(xw, sheet_name="Cartera completa", index=False)
    return cartera
