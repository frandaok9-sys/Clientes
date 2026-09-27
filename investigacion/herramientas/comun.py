"""Funciones compartidas por sumar.py y completar.py."""
import pandas as pd
from prospeccion import mensajes


def borrador(o, r, cfg):
    """Arma el borrador de una fila investigada (o) con las frases del rubro (r). Devuelve (nombre_corto, texto)."""
    genericos = cfg["emails_genericos"]; GEN = cfg["industrial_generico"]
    saludo = mensajes.saludo_nombre(pd.Series({"contacto_nombre": o["contacto_nombre"], "razon_social": o["razon_social"],
                                               "nombre_fantasia": o["nombre_corto"], "email": o["contacto_email"] or None}), genericos)
    corto = o["nombre_corto"] or mensajes.nombre_corto(pd.Series({"razon_social": o["razon_social"]}))
    dato = o["dato"].rstrip(". ")
    apertura = f"Vi que {dato}." if dato else f"Te escribo porque vi que {corto} {r.get('frase', GEN['frase'])}."
    b = (f"Hola{' ' + saludo if saludo else ''}, soy {cfg['oferta']['remitente']}, de COI.\n{apertura}\n"
         f"En empresas así, {r['dolor']}.\nCOI {r['solucion']}.\n{cfg['oferta']['cta']}\n— {cfg['oferta']['baja']}")
    if len(b.split()) > 90:
        b = (f"Hola{' ' + saludo if saludo else ''}, soy {cfg['oferta']['remitente']}, de COI.\n{apertura}\n"
             f"COI {r['solucion']}.\n{cfg['oferta']['cta']}\n— {cfg['oferta']['baja']}")
    assert len(b.split()) <= 90, o["razon_social"]
    return corto, b
