from pathlib import Path

import pandas as pd
import pytest
import yaml

from prospeccion import clasificacion, cli, limpieza, mensajes, seguimiento

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))


def test_normalizacion():
    assert limpieza.normalizar_cuit("30-71234567-1") == "30-71234567-1"
    assert limpieza.normalizar_cuit("30712345672") is None  # dígito verificador incorrecto
    assert limpieza.normalizar_telefono("(0264) 422-1234", "AR") == "+542644221234"
    assert limpieza.normalizar_telefono("0341 15 555-1234", "AR") == "+5493415551234"
    assert limpieza.dominio_web("https://www.Empresa.com.ar/obras") == "empresa.com.ar"
    assert limpieza.nombre_normalizado("Montajes del Sur S.R.L.") == limpieza.nombre_normalizado("Montajes del Sur SRL")
    assert limpieza.a_numero("10-20") == 15


def _procesar(bajas=None):
    df = limpieza.mapear_columnas(limpieza.cargar(RAIZ / "datos/ejemplo_clientes.csv"), CONFIG["columnas"])
    df["fuente"] = "ejemplo"
    df, dup = limpieza.deduplicar(limpieza.limpiar(df, "AR"))
    df = clasificacion.calificar(df, CONFIG, bajas or set(), verificar_mx=False)
    return mensajes.generar(df, RAIZ / "plantillas", CONFIG), dup


def _fila(df, texto):
    return df[df["razon_social"].str.contains(texto, na=False)].iloc[0]


def test_calificacion_y_descartes():
    df, dup = _procesar()
    assert dup == 1  # Montajes del Sur SRL / S.R.L. en la misma localidad
    montajes = _fila(df, "Montajes")
    assert montajes["categoria"] == "A" and montajes["rubro_coi"].startswith("Montajes")
    assert montajes["verificar_no_llame"] == "sí"
    assert montajes["email_estado"] == "generico"
    assert _fila(df, "Kiosco")["motivo_descarte"] == "consumidor final / B2C"
    assert _fila(df, "Aceros")["motivo_descarte"].startswith("gran empresa con ERP")
    assert _fila(df, "RC Pisos")["motivo_descarte"] == "cliente actual de COI"
    assert _fila(df, "Sistemas Gestión")["motivo_descarte"].startswith("competidor")
    assert _fila(df, "Juan Pérez")["categoria"] == "C - chico"
    dist = _fila(df, "Distribuidora")
    assert dist["requiere_dominio"] == "sí" and pd.isna(dist["dominio_email"])


def test_bajas_se_respetan():
    df, _ = _procesar(bajas={"30-71234567-1"})
    assert _fila(df, "Montajes")["motivo_descarte"] == "oposición registrada (baja)"


def test_borradores():
    df, _ = _procesar()
    for _, fila in df[df["categoria"].isin(["A", "B"])].iterrows():
        texto = fila["borrador"]
        assert "COI" in texto and texto.endswith("respondé BAJA y no te escribimos más.")
        assert len(texto.split()) <= 95, texto
        assert "$" not in texto
    assert pd.isna(_fila(df, "Kiosco")["borrador"])


def test_entrega_y_seguimiento(tmp_path):
    df, _ = _procesar()
    out = cli.entrega(df)
    assert list(out.columns) == cli.COLUMNAS_ENTREGA
    bajas = tmp_path / "bajas.csv"
    with seguimiento.conectar(tmp_path / "t.db") as con:
        seguimiento.guardar_empresas(out, con)
        cola = seguimiento.cola(con)
        assert set(cola["cat"]) <= {"A", "B"}
        eid = int(cola.iloc[0]["id"])
        assert seguimiento.registrar(con, eid, "email", "baja", ruta_bajas=bajas) == "baja"
        assert eid not in seguimiento.cola(con)["id"].tolist()
        with pytest.raises(ValueError):
            seguimiento.registrar(con, eid, "email", "inventado")
    assert "30-71234567-1" in seguimiento.leer_bajas(bajas)


def test_emails_comodin_y_personas():
    df = pd.DataFrame({"razon_social": ["A SA", "B SA", "C SA", "D SA"],
                       "email": ["x@gmail.com", "x@gmail.com", "x@gmail.com", "d@d.com.ar"]})
    df, n = limpieza.descartar_emails_compartidos(df, 3)
    assert n == 3 and df["email"].notna().sum() == 1
    fila = pd.Series({"razon_social": "Gomez Juan", "persona_fisica": True, "pais": "Argentina",
                      "email": None, "telefono": None, "web": None, "empleados": None})
    r = clasificacion.calificar_fila(fila, CONFIG, set(), None)
    assert r["categoria"] == "C - chico"
    grande = clasificacion.calificar_fila(pd.Series({"razon_social": "Cargill SACI", "email": None}), CONFIG, set(), None)
    assert grande["motivo_descarte"].startswith("gran empresa")
    club = clasificacion.calificar_fila(pd.Series({"razon_social": "Club Atletico X", "email": None}), CONFIG, set(), None)
    assert club["categoria"] == "Descartada"
    otro = clasificacion.calificar_fila(pd.Series({"razon_social": "Tico Pisos Industriales SRL", "email": None}),
                                        CONFIG, set(), None)
    assert pd.isna(otro["motivo_descarte"])


def test_saludo_y_nombre_corto():
    gen = CONFIG["emails_genericos"]
    base = {"razon_social": "MINERA SAN PEDRO SRL", "nombre_fantasia": None}
    assert mensajes.nombre_corto(pd.Series(base)) == "Minera San Pedro"
    # el "contacto" es la propia empresa
    assert mensajes.saludo_nombre(pd.Series({**base, "contacto_nombre": "Minera San Pedro Srl", "email": None}), gen) == ""
    # email personal de otra persona: no se saluda por nombre
    assert mensajes.saludo_nombre(pd.Series({**base, "contacto_nombre": "Horacio Pinasco", "email": "bmonge@x.com.ar"}), gen) == ""
    # email de la misma persona o genérico: sí
    assert mensajes.saludo_nombre(pd.Series({**base, "contacto_nombre": "Horacio Pinasco", "email": "hpinasco@x.com.ar"}), gen) == "Horacio"
    assert mensajes.saludo_nombre(pd.Series({**base, "contacto_nombre": "Horacio Pinasco", "email": "ventas@x.com.ar"}), gen) == "Horacio"


def test_rubro_informado_manda_sobre_el_nombre():
    fila = pd.Series({"razon_social": "Distribuidora Dique SRL", "rubro": "librería mayorista", "email": None})
    assert pd.isna(clasificacion.calificar_fila(fila, CONFIG, set(), None)["rubro_coi"])
    fila = pd.Series({"razon_social": "Distribuidora Dique SRL", "email": None})
    assert clasificacion.calificar_fila(fila, CONFIG, set(), None)["rubro_coi"].startswith("Distribuidoras")


def test_dedupe_prefiere_fuente_mas_confiable():
    df = pd.DataFrame({
        "razon_social": ["Metal X SRL", "Metal X SRL"], "localidad": ["Rosario", "Rosario"],
        "email": ["viejo@metalx.com.ar", "ventas@metalx.com.ar"], "rubro": ["metalurgica", None],
        "_confianza": [1, 3],
    })
    for c in limpieza.CAMPOS:
        if c not in df.columns:
            df[c] = pd.NA
    out, n = limpieza.deduplicar(df)
    assert n == 1 and out.iloc[0]["email"] == "ventas@metalx.com.ar" and out.iloc[0]["rubro"] == "metalurgica"


def test_revision_manual_manda():
    fila = pd.Series({"razon_social": "Metal Y SRL", "senales": "cerrada", "email": None})
    assert clasificacion.calificar_fila(fila, CONFIG, set(), None)["categoria"] == "Descartada"
    rev = {limpieza.nombre_normalizado("Metal Y SRL"): ("mantener", "sigue activa")}
    assert clasificacion.calificar_fila(fila, CONFIG, set(), None, rev)["categoria"] != "Descartada"
