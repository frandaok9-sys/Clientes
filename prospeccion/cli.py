"""Línea de comandos: python -m prospeccion <comando>."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import clasificacion, limpieza, mensajes, seguimiento

app = typer.Typer(help="Limpia, clasifica, cualifica y prospecta listas de clientes.", no_args_is_help=True)
consola = Console()
RAIZ = Path(__file__).resolve().parent.parent


def _config(ruta: Path) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _db(config: dict) -> Path:
    return RAIZ / config.get("base_datos", "datos/salida/prospeccion.db")


def _tabla(df: pd.DataFrame, titulo: str) -> None:
    t = Table(title=titulo)
    for col in df.columns:
        t.add_column(str(col))
    for _, fila in df.iterrows():
        t.add_row(*["" if pd.isna(v) else str(v) for v in fila])
    consola.print(t)


OpcionConfig = typer.Option(RAIZ / "config.yaml", "--config", "-c", help="Archivo de configuración")


@app.command()
def procesar(
    entradas: list[Path] = typer.Argument(..., help="Uno o varios CSV/Excel con clientes"),
    salida: Path = typer.Option(RAIZ / "datos/salida", "--salida", "-o"),
    reiniciar: bool = typer.Option(False, "--reiniciar", help="Sobrescribe el seguimiento existente"),
    config_path: Path = OpcionConfig,
):
    """Importa, limpia, deduplica, puntúa, segmenta y genera mensajes. Crea Excel + base de seguimiento."""
    config = _config(config_path)
    with seguimiento.conectar(_db(config)) as con:
        if seguimiento.hay_seguimiento(con) and not reiniciar:
            consola.print("[red]Ya hay llamadas/mensajes registrados. Usa 'exportar' para guardarlos y "
                          "'procesar --reiniciar' para empezar de cero.[/]")
            raise typer.Exit(1)
    pais = config.get("pais_por_defecto", "ES")

    marcos = []
    for ruta in entradas:
        df = limpieza.mapear_columnas(limpieza.cargar(ruta), config.get("columnas", {}))
        df["origen"] = ruta.name
        marcos.append(df)
    bruto = pd.concat(marcos, ignore_index=True)
    total = len(bruto)

    limpio = limpieza.limpiar(bruto, pais)
    sin_datos = total - len(limpio)
    limpio, duplicados = limpieza.deduplicar(limpio)
    clasificado = clasificacion.clasificar(limpio, config)
    final = mensajes.generar(clasificado, RAIZ / "plantillas", config.get("oferta", {}))

    salida.mkdir(parents=True, exist_ok=True)
    excel = salida / "clientes_clasificados.xlsx"
    with pd.ExcelWriter(excel, engine="openpyxl") as xw:
        final.to_excel(xw, sheet_name="Todos", index=False)
        for seg in ("A", "B", "C"):
            final[final["segmento"] == seg].to_excel(xw, sheet_name=f"Segmento {seg}", index=False)
        cols_llamada = ["segmento", "puntuacion", "nombre", "empresa", "telefono", "ciudad", "motivos", "guion_llamada"]
        final[final["canal"] == "llamada"][cols_llamada].to_excel(xw, sheet_name="Llamadas", index=False)
        cols_wa = ["segmento", "nombre", "empresa", "telefono", "enlace_whatsapp", "mensaje_whatsapp"]
        final[final["canal"] == "whatsapp"][cols_wa].to_excel(xw, sheet_name="WhatsApp", index=False)
        cols_mail = ["segmento", "nombre", "empresa", "email", "email_asunto", "email_cuerpo"]
        final[final["canal"] == "email"][cols_mail].to_excel(xw, sheet_name="Email", index=False)
        final[final["canal"] == "sin_contacto"].to_excel(xw, sheet_name="Sin contacto", index=False)
    final.to_csv(salida / "clientes_clasificados.csv", index=False)

    with seguimiento.conectar(_db(config)) as con:
        seguimiento.guardar_clientes(final, con)

    consola.print(f"[bold]Registros leídos:[/] {total}  |  sin datos: {sin_datos}  |  duplicados fusionados: {duplicados}")
    consola.print(f"[bold]Clientes finales:[/] {len(final)}")
    _tabla(final.groupby(["segmento", "canal"]).size().reset_index(name="clientes"), "Segmentos y canal")
    consola.print(f"[green]Excel:[/] {excel}\n[green]Seguimiento:[/] {_db(config)}")


@app.command()
def cola(
    canal: str = typer.Option(None, help="llamada | whatsapp | email"),
    limite: int = typer.Option(20),
    config_path: Path = OpcionConfig,
):
    """Muestra los siguientes clientes a contactar, por prioridad."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        _tabla(seguimiento.cola(con, canal, limite), "Cola de contacto")


@app.command()
def registrar(
    cliente_id: int = typer.Argument(..., help="ID del cliente (ver 'cola')"),
    resultado: str = typer.Argument(..., help=" | ".join(seguimiento.RESULTADOS)),
    canal: str = typer.Option("llamada", help="llamada | whatsapp | email"),
    nota: str = typer.Option("", help="Comentario libre"),
    proximo: str = typer.Option("", help="Próximo paso / fecha"),
    config_path: Path = OpcionConfig,
):
    """Registra el resultado de una llamada o mensaje y actualiza el estado del cliente."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        try:
            estado = seguimiento.registrar(con, cliente_id, canal, resultado, nota, proximo)
        except ValueError as e:
            consola.print(f"[red]{e}[/]")
            raise typer.Exit(1)
    consola.print(f"Cliente {cliente_id} -> [bold]{estado}[/]")


@app.command()
def resumen(config_path: Path = OpcionConfig):
    """Resumen del pipeline por segmento y estado."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        df = seguimiento.resumen(con)
    _tabla(df.pivot_table(index="segmento", columns="estado", values="clientes", aggfunc="sum", fill_value=0).astype(int).reset_index(),
           "Pipeline")


@app.command()
def exportar(
    archivo: Path = typer.Option(RAIZ / "datos/salida/seguimiento.xlsx", "--archivo", "-o"),
    config_path: Path = OpcionConfig,
):
    """Exporta clientes (con su estado actual) e historial de interacciones a Excel."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        clientes = pd.read_sql_query("SELECT * FROM clientes", con)
        historial = pd.read_sql_query(
            "SELECT i.*, c.nombre, c.empresa FROM interacciones i JOIN clientes c ON c.id = i.cliente_id "
            "ORDER BY i.fecha DESC", con)
    with pd.ExcelWriter(archivo, engine="openpyxl") as xw:
        clientes.to_excel(xw, sheet_name="Clientes", index=False)
        historial.to_excel(xw, sheet_name="Interacciones", index=False)
    consola.print(f"[green]Exportado:[/] {archivo}")


if __name__ == "__main__":
    app()
