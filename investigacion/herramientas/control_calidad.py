"""Control de calidad del CSV de prospectos antes de republicar el tablero o de que el usuario empiece a enviar.

Uso (desde la raíz del repo):
    PYTHONPATH=. python investigacion/herramientas/control_calidad.py
Revisa cada empresa y lista lo que conviene corregir a mano:
- emails mal formados, marcados «deducido» o de un dominio sin servidor de correo (rebotarían);
- el mismo email en varias empresas;
- teléfonos sin `verificar_no_llame = sí`;
- borradores sin COI, sin la línea de baja o con palabras que el brief prohíbe (AFIP, ARCA, precio);
- decisores de A/B que salen de una fuente anterior a 2019 (conviene confirmar que sigan a cargo).
No cambia nada: solo informa.
"""
import collections
import re

import dns.resolver
import pandas as pd

p = pd.read_csv("canal/respuestas/20260926-prospectos-AB.csv", sep=";", dtype=str).fillna("")
FORMATO = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", re.I)
dominios, repetidos, avisos = {}, collections.Counter(), []


def dominio_recibe(d):
    if d not in dominios:
        try:
            dns.resolver.resolve(d, "MX", lifetime=8)
            dominios[d] = ""
        except Exception as ex:
            dominios[d] = type(ex).__name__
    return dominios[d]


for r in p.itertuples():
    emails = [e.strip() for e in re.split(r"[ /,|]+", r.contacto_email) if "@" in e]
    if r.contacto_email and not emails:
        avisos.append((r.categoria, r.razon_social, "email sin @", r.contacto_email))
    for e in emails:
        repetidos[e.lower()] += 1
        if not FORMATO.match(e):
            avisos.append((r.categoria, r.razon_social, "email mal formado", e))
        elif error := dominio_recibe(e.split("@")[1].lower()):
            avisos.append((r.categoria, r.razon_social, f"dominio sin correo ({error})", e))
    if "deducido" in r.contacto_email.lower():
        avisos.append((r.categoria, r.razon_social, "email deducido", r.contacto_email))
    if r.contacto_telefono and r.verificar_no_llame != "sí":
        avisos.append((r.categoria, r.razon_social, "teléfono sin No Llame", r.contacto_telefono))
    if r.borrador:
        if "COI" not in r.borrador:
            avisos.append((r.categoria, r.razon_social, "borrador sin COI", ""))
        if "respondé BAJA" not in r.borrador:
            avisos.append((r.categoria, r.razon_social, "borrador sin línea de baja", ""))
        for palabra in ("AFIP", "ARCA", "[Pp]recios?"):
            if re.search(rf"\b{palabra}\b", r.borrador):
                avisos.append((r.categoria, r.razon_social, f"borrador menciona {palabra}", ""))
        if re.search("[ÃÂâ][\x80-\xbf€“”™]", r.borrador):
            avisos.append((r.categoria, r.razon_social, "borrador con tildes rotas", ""))
    anios = [int(a) for a in re.findall(r"(19\d\d|20[0-2]\d)", r.contacto_cargo)]
    if r.categoria in ("A", "B") and r.contacto_nombre and anios and max(anios) < 2019:
        avisos.append((r.categoria, r.razon_social, f"decisor con dato de {max(anios)}", r.contacto_nombre))
for e, n in repetidos.items():
    if n > 1:
        avisos.append(("", "(varias)", f"email repetido en {n} empresas", e))

print(f"{len(p)} empresas, {len(dominios)} dominios de email chequeados, {len(avisos)} avisos")
for cat, razon, tipo, dato in sorted(avisos, key=lambda a: (a[2], a[0], a[1])):
    print(f"{cat or '-'} | {razon} | {tipo} | {dato}")
