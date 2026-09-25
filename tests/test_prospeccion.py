from pathlib import Path

import pandas as pd
import yaml

from prospeccion import clasificacion, limpieza, mensajes, seguimiento

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))


def test_telefono_y_email():
    assert limpieza.normalizar_telefono("612 345 678", "ES") == "+34612345678"
    assert limpieza.normalizar_telefono("0034 699 111 222", "ES") == "+34699111222"
    assert limpieza.normalizar_telefono("123", "ES") is None
    assert limpieza.normalizar_email(" Juan@ElPuerto.es ") == "juan@elpuerto.es"
    assert limpieza.normalizar_email("pedro@@taller") is None


def test_a_numero():
    assert limpieza.a_numero("450.000") == 450000
    assert limpieza.a_numero("1,2M") == 1_200_000
    assert limpieza.a_numero("80k") == 80_000
    assert limpieza.a_numero("10-20") == 15
    assert limpieza.a_numero("abc") is None


def _procesar():
    df = limpieza.mapear_columnas(limpieza.cargar(RAIZ / "datos/ejemplo_clientes.csv"), CONFIG["columnas"])
    df, dup = limpieza.deduplicar(limpieza.limpiar(df, "ES"))
    return clasificacion.clasificar(df, CONFIG), dup


def test_deduplica_y_clasifica():
    df, dup = _procesar()
    assert dup == 1
    juan = df[df["empresa"] == "Restaurante El Puerto"].iloc[0]
    assert juan["segmento"] == "A" and juan["canal"] == "llamada"
    carlos = df[df["nombre"] == "Carlos Ruiz"].iloc[0]
    assert carlos["canal"] == "email"  # sin teléfono: se degrada a email
    assert set(df["segmento"]) <= {"A", "B", "C"}


def test_mensajes_y_seguimiento(tmp_path):
    df, _ = _procesar()
    df = mensajes.generar(df, RAIZ / "plantillas", CONFIG["oferta"])
    fila = df[df["empresa"] == "Restaurante El Puerto"].iloc[0]
    assert fila["enlace_whatsapp"].startswith("https://wa.me/34612345678?text=Hola%20Juan")
    assert "Restaurante El Puerto" in fila["email_asunto"]

    with seguimiento.conectar(tmp_path / "t.db") as con:
        seguimiento.guardar_clientes(df, con)
        assert len(seguimiento.cola(con)) == len(df)
        assert seguimiento.registrar(con, 1, "llamada", "no_interesado") == "perdido"
        assert 1 not in seguimiento.cola(con)["id"].tolist()
