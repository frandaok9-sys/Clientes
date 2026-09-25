"""Calificación de empresas para COI: rubro, puntaje, categoría y descartes (brief, secciones 3–5)."""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz

from .limpieza import clave, nombre_normalizado, vacio


@lru_cache(maxsize=None)
def _patron(palabras: tuple[str, ...]) -> re.Pattern | None:
    palabras = tuple(p for p in (clave(x) for x in palabras) if p)
    if not palabras:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(p) for p in palabras) + r")\b")


def _verdadero(valor) -> bool:
    return not vacio(valor) and bool(valor)


def coincide(texto: str, palabras) -> str | None:
    """Devuelve la primera palabra clave encontrada (por palabra completa) o None."""
    patron = _patron(tuple(palabras or ()))
    if patron is None or not texto:
        return None
    m = patron.search(texto)
    return m.group(1) if m else None


def _texto(fila: pd.Series, campos) -> str:
    return " ".join(clave(fila.get(c)) for c in campos if not vacio(fila.get(c)))


# --- Google Workspace -------------------------------------------------------------------------

def dominio_email(fila: pd.Series, gratuitos: set[str]) -> tuple[str | None, bool]:
    """(dominio, es_propio). Usa el dominio del email; si no hay email, el de la web."""
    if not vacio(fila.get("email")):
        dom = str(fila["email"]).split("@")[1]
        return dom, dom not in gratuitos
    if not vacio(fila.get("web")):
        return fila["web"], True
    return None, False


def usa_google_workspace(dominio: str, cache: dict) -> str:
    """'sí' / 'no' / 'sin verificar' según los registros MX del dominio."""
    if dominio in cache:
        return cache[dominio]
    try:
        import dns.resolver

        mx = [str(r.exchange).lower() for r in dns.resolver.resolve(dominio, "MX", lifetime=5)]
        res = "sí" if any(m.rstrip(".").endswith(("google.com", "googlemail.com")) for m in mx) else "no"
    except Exception as e:  # noqa: BLE001 - cualquier fallo de DNS deja el dato sin verificar
        res = "no" if type(e).__name__ in {"NXDOMAIN", "NoAnswer"} else "sin verificar"
    cache[dominio] = res
    return res


# --- Calificación -----------------------------------------------------------------------------

def detectar_rubro(texto: str, config: dict) -> tuple[dict | None, bool]:
    """(rubro, es_prioritario). Recorre los rubros prioritarios en orden y luego el genérico."""
    for rubro in config.get("rubros", []):
        if coincide(texto, rubro["palabras"]):
            return rubro, True
    gen = config.get("industrial_generico", {})
    if coincide(texto, gen.get("palabras")):
        return {"nombre": "Industrial B2B (otro)", **gen}, False
    return None, False


def motivo_descarte(fila: pd.Series, texto: str, config: dict) -> str | None:
    d = config.get("descartes", {})
    rubro_txt = _texto(fila, ["rubro"])
    nombre_txt = _texto(fila, ["razon_social", "nombre_fantasia"])
    dominio_mail = str(fila["email"]).split("@")[1] if not vacio(fila.get("email")) else ""
    if not vacio(fila.get("pais")) and clave(fila["pais"]) not in {clave(p) for p in d.get("paises_permitidos", [])}:
        return "fuera de Argentina"
    nombres = [nombre_normalizado(fila.get("razon_social")), nombre_normalizado(fila.get("nombre_fantasia"))]
    for cliente in d.get("clientes_actuales", []):
        ref = nombre_normalizado(cliente)
        if any(n and fuzz.ratio(n, ref) >= 95 for n in nombres):
            return "cliente actual de COI"
    grande = coincide(nombre_txt, d.get("grandes_conocidas")) or coincide(clave(dominio_mail.split(".")[0]), d.get("grandes_conocidas"))
    if grande:
        return f"gran empresa ({grande})"
    if any(dominio_mail.endswith(x) for x in d.get("dominios_publicos", [])):
        return "sector público"
    entidad = coincide(nombre_txt, d.get("no_empresa"))
    if entidad:
        return f"no es empresa objetivo ({entidad})"
    if coincide(rubro_txt, d.get("competidores")):
        return "competidor (software de gestión)"
    if coincide(rubro_txt, d.get("b2c")):
        return "consumidor final / B2C"
    emp = fila.get("empleados")
    erp = coincide(texto, d.get("erp_corporativo"))
    if (not vacio(emp) and emp > d.get("empleados_grande", 250)) and erp:
        return f"gran empresa con ERP corporativo ({erp.upper()})"
    if not vacio(emp) and emp > d.get("empleados_grande", 250):
        return "gran empresa (más de 250 empleados)"
    return None


def calificar_fila(fila: pd.Series, config: dict, bajas: set[str], mx_cache: dict | None) -> dict:
    p = config.get("puntaje", {})
    s = config.get("senales", {})
    texto = _texto(fila, ["rubro", "razon_social", "nombre_fantasia", "web", "senales"])
    senales_txt = _texto(fila, ["senales", "rubro"])

    dominio, propio = dominio_email(fila, set(config.get("correo_gratuito", [])))
    workspace = "sin verificar"
    if dominio and propio and mx_cache is not None:
        workspace = usa_google_workspace(dominio, mx_cache)
    elif dominio and not propio:
        workspace = "no"

    rubro, prioritario = detectar_rubro(texto, config)
    puntos, senales, hechos = 0, [], []

    def sumar(n, etiqueta):
        nonlocal puntos
        puntos += n
        senales.append(f"{etiqueta} (+{n})")

    if rubro and prioritario:
        sumar(p.get("rubro_prioritario", 3), "rubro prioritario")
    elif rubro:
        sumar(p.get("rubro_industrial_no_listado", 1), "industrial B2B no listado")
    emp = fila.get("empleados")
    if not vacio(emp) and p.get("tamano_min", 10) <= emp <= p.get("tamano_max", 100):
        sumar(p.get("tamano_en_rango", 2), f"{int(emp)} empleados")
    for criterio, etiqueta in (("vendedores", "área comercial"), ("proyectos_campo", "proyectos/obras"),
                               ("usd_mineria_energia", "USD/minería/energía"), ("crecimiento", "crecimiento")):
        hallado = coincide(senales_txt if criterio != "usd_mineria_energia" else texto, s.get(criterio))
        if hallado:
            sumar(p.get(criterio, 1), f"{etiqueta}: «{hallado}»")
            hechos.append(criterio)
    if workspace == "sí":
        sumar(p.get("google_workspace", 1), "Google Workspace (MX)")
    cargo = coincide(_texto(fila, ["contacto_cargo"]), s.get("cargos_decision"))
    if cargo and not vacio(fila.get("contacto_nombre")):
        sumar(p.get("contacto_decision", 1), f"decisor: {fila['contacto_cargo']}")

    c = config.get("categorias", {})
    categoria = "A" if puntos >= c.get("A", 10) else "B" if puntos >= c.get("B", 6) else "C"

    motivo = motivo_descarte(fila, texto, config)
    identificadores = {clave(x) for x in (fila.get("cuit"), fila.get("email"), fila.get("telefono"), dominio) if not vacio(x)}
    if identificadores & bajas:
        motivo = "oposición registrada (baja)"
    if motivo:
        categoria = "Descartada"
    elif (not vacio(emp) and emp <= 1) or coincide(texto, config.get("descartes", {}).get("unipersonal")):
        categoria, motivo = "C - chico", None
    elif _verdadero(fila.get("persona_fisica")) and (vacio(emp) or emp < p.get("tamano_min", 10)):
        categoria = "C - chico"
        senales.append("persona física, sin datos de equipo")

    return {
        "rubro_coi": rubro["nombre"] if rubro else pd.NA,
        "plan_sugerido": rubro.get("plan") if rubro and categoria in ("A", "B") else pd.NA,
        "dominio_email": dominio if propio else pd.NA,
        "requiere_dominio": "no" if propio else "sí",
        "usa_google_workspace": workspace,
        "señales": "; ".join(senales),
        "puntaje": puntos,
        "categoria": categoria,
        "motivo_descarte": motivo or pd.NA,
        "_dolor": rubro.get("dolor") if rubro else None,
        "_solucion": rubro.get("solucion") if rubro else None,
        "_hechos": ",".join(hechos),
    }


def estado_email(fila: pd.Series, genericos: set[str]) -> str | None:
    """generico | deducido | verificado | sin_verificar. Respeta el valor de la lista si viene marcado."""
    if vacio(fila.get("email")):
        return None
    if not vacio(fila.get("email_estado")) and clave(fila["email_estado"]) in {"verificado", "deducido", "generico"}:
        return clave(fila["email_estado"])
    local = str(fila["email"]).split("@")[0]
    if any(local.startswith(g) for g in genericos):
        return "generico"
    return "sin_verificar"


_SOCIEDAD = re.compile(r"\b(s\.?\s?a\.?\s?s?|s\.?\s?r\.?\s?l|s\.?\s?a\.?\s?i\.?\s?c|sociedad)\b", re.IGNORECASE)


def prioridad_enriquecimiento(fila: pd.Series) -> int:
    """Qué tan útil es investigar esta empresa en la web (0 = no vale la pena).

    Sirve para elegir qué mandar a enriquecer cuando la lista no trae rubro ni tamaño.
    """
    if fila["categoria"] in ("Descartada", "C - chico"):
        return 0
    p = 0
    p += 3 if fila["puntaje"] >= 3 else fila["puntaje"]              # rubro detectado
    p += 2 if _SOCIEDAD.search(str(fila.get("razon_social") or "")) or str(fila.get("cuit") or "").startswith(("30", "33")) else 0
    p += 1 if not vacio(fila.get("dominio_email")) else 0
    p += 1 if not vacio(fila.get("telefono")) else 0
    p += 1 if not vacio(fila.get("localidad")) else 0
    return p


def calificar(df: pd.DataFrame, config: dict, bajas: set[str] | None = None,
              verificar_mx: bool = False) -> pd.DataFrame:
    df = df.copy()
    cache = {} if verificar_mx else None
    if verificar_mx:
        from concurrent.futures import ThreadPoolExecutor

        gratuitos = set(config.get("correo_gratuito", []))
        dominios = {d for d, propio in (dominio_email(f, gratuitos) for _, f in df.iterrows()) if d and propio}
        with ThreadPoolExecutor(max_workers=32) as ex:
            for dom, res in zip(dominios, ex.map(lambda d: usa_google_workspace(d, {}), dominios)):
                cache[dom] = res
    extra = pd.DataFrame([calificar_fila(f, config, bajas or set(), cache) for _, f in df.iterrows()])
    df = pd.concat([df.reset_index(drop=True), extra], axis=1)
    genericos = set(config.get("emails_genericos", []))
    df["email_estado"] = df.apply(lambda f: estado_email(f, genericos), axis=1)
    df["verificar_no_llame"] = df["telefono"].apply(lambda t: "sí" if not vacio(t) else pd.NA)
    df["fecha_revision"] = date.today().isoformat()
    df["prioridad_enriquecimiento"] = df.apply(prioridad_enriquecimiento, axis=1)
    orden = {"A": 0, "B": 1, "C": 2, "C - chico": 3, "Descartada": 4}
    df["_orden"] = df["categoria"].map(orden)
    return df.sort_values(["_orden", "puntaje"], ascending=[True, False]).drop(columns="_orden").reset_index(drop=True)
