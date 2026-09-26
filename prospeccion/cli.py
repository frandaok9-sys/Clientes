"""Línea de comandos: python -m prospeccion <comando>."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import clasificacion, importar, limpieza, mensajes, seguimiento

app = typer.Typer(help="Limpia, califica y prepara la prospección de empresas para COI.", no_args_is_help=True)
consola = Console()
RAIZ = Path(__file__).resolve().parent.parent

# Formato de entrega (brief, sección 8) + requiere_dominio (sección 4)
COLUMNAS_ENTREGA = [
    "razon_social", "nombre_fantasia", "cuit", "rubro_coi", "localidad", "provincia", "web", "dominio_email",
    "usa_google_workspace", "empleados_aprox", "usuarios_probables", "señales", "puntaje", "categoria",
    "motivo_descarte", "plan_sugerido", "contacto_nombre", "contacto_cargo", "contacto_email", "email_estado",
    "contacto_telefono", "verificar_no_llame", "angulo_primer_contacto", "fuente", "fecha_revision",
    "requiere_dominio", "fuente_enriquecimiento",
]


def confianza(ruta: Path) -> int:
    """Qué dato manda al unir duplicados: verificado en la web > enriquecido > cartera original."""
    texto = str(ruta).lower()
    if "verificar" in texto:
        return 3
    if "respuestas" in texto:      # enriquecimiento de la sesión local, abriendo las webs
        return 2
    if "enriquecimiento" in texto:  # enriquecimiento por búsqueda web
        return 1
    return 0


def _config(ruta: Path) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _ruta(config: dict, clave: str, defecto: str) -> Path:
    return RAIZ / config.get(clave, defecto)


def _db(config: dict) -> Path:
    return _ruta(config, "base_datos", "datos/salida/prospeccion.db")


def _tabla(df: pd.DataFrame, titulo: str) -> None:
    t = Table(title=titulo)
    for col in df.columns:
        t.add_column(str(col))
    for _, fila in df.iterrows():
        t.add_row(*["" if limpieza.vacio(v) else str(v) for v in fila])
    consola.print(t)


def entrega(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"email": "contacto_email", "telefono": "contacto_telefono"}).copy()
    out["empleados_aprox"] = out["empleados"].apply(lambda v: pd.NA if limpieza.vacio(v) else int(v))
    if "fuente_enriquecimiento" not in out.columns:
        out["fuente_enriquecimiento"] = pd.NA
    if "usuarios_probables" not in out.columns:
        out["usuarios_probables"] = pd.NA  # no se estima: no se inventan datos
    return out[COLUMNAS_ENTREGA]


def texto_resumen(total: int, sin_datos: int, duplicados: int, df: pd.DataFrame) -> str:
    cats = df["categoria"].value_counts()
    lineas = [
        f"- Filas que entraron: {total}",
        f"- Filas sin identificación (sin razón social, fantasía, CUIT ni web): {sin_datos}",
        f"- Duplicados eliminados: {duplicados}",
        f"- Empresas finales: {len(df)}",
        f"- A: {cats.get('A', 0)} | B: {cats.get('B', 0)} | C: {cats.get('C', 0)} | "
        f"C - chico: {cats.get('C - chico', 0)} | Descartadas: {cats.get('Descartada', 0)}",
    ]
    descartes = df.loc[df["categoria"] == "Descartada", "motivo_descarte"]
    for motivo, n in descartes.str.replace(r" \(.*\)$", "", regex=True).value_counts().items():
        detalle = descartes[descartes.str.startswith(motivo)].str.extract(r"\((.*)\)$")[0].dropna().value_counts()
        ejemplos = f" (p. ej. {', '.join(detalle.index[:5])})" if len(detalle) else ""
        lineas.append(f"  - {motivo}: {n}{ejemplos}")
    top = df.loc[df["categoria"] == "A", "rubro_coi"].value_counts().head(3)
    lineas.append("- Rubros con más A: " + (", ".join(f"{r} ({n})" for r, n in top.items()) or "ninguno"))
    return "\n".join(lineas)


OpcionConfig = typer.Option(RAIZ / "config.yaml", "--config", "-c", help="Archivo de configuración")


@app.command()
def procesar(
    entradas: list[Path] = typer.Argument(..., help="Uno o varios CSV/Excel con empresas"),
    salida: Path = typer.Option(RAIZ / "datos/salida", "--salida", "-o"),
    verificar_mx: bool = typer.Option(False, "--verificar-mx", help="Consulta DNS para detectar Google Workspace"),
    reiniciar: bool = typer.Option(False, "--reiniciar", help="Sobrescribe el seguimiento existente"),
    config_path: Path = OpcionConfig,
):
    """Limpia, deduplica, califica, descarta y prepara borradores. Genera el CSV de entrega y un Excel de trabajo."""
    config = _config(config_path)
    with seguimiento.conectar(_db(config)) as con:
        if seguimiento.hay_seguimiento(con) and not reiniciar:
            consola.print("[red]Ya hay contactos registrados. Usá 'exportar' para guardarlos y "
                          "'procesar --reiniciar' para empezar de cero (las bajas se conservan).[/]")
            raise typer.Exit(1)

    marcos = []
    for ruta in entradas:
        if importar.es_formato_propio(ruta, config.get("columnas", {})):
            df = importar.importar(ruta)  # RAI, AG-360, PDF de zonas
        else:
            df = limpieza.cargar(ruta)
        df = limpieza.mapear_columnas(df, config.get("columnas", {}))
        df["fuente"] = df["fuente"].fillna(ruta.name)
        df["_confianza"] = confianza(ruta)
        consola.print(f"{ruta.name}: {len(df)} filas")
        marcos.append(df)
    bruto = pd.concat(marcos, ignore_index=True)
    total = len(bruto)

    limpio = limpieza.limpiar(bruto, config.get("pais_por_defecto", "AR"))
    sin_datos = total - len(limpio)
    limpio, comodines = limpieza.descartar_emails_compartidos(limpio, config.get("email_compartido_max", 3))
    limpio, duplicados = limpieza.deduplicar(limpio)
    bajas = seguimiento.leer_bajas(_ruta(config, "bajas", "datos/bajas.csv"))
    calificado = clasificacion.calificar(limpio, config, bajas, verificar_mx)
    final = mensajes.generar(calificado, RAIZ / "plantillas", config)

    salida.mkdir(parents=True, exist_ok=True)
    tabla_entrega = entrega(final)
    tabla_entrega.to_csv(salida / "entrega.csv", sep=";", index=False, encoding="utf-8")
    resumen_md = texto_resumen(total, sin_datos, duplicados, final)
    resumen_md += f"\n- Emails comodín vaciados (repetidos en {config.get('email_compartido_max', 3)}+ empresas): {comodines}"
    candidatos = final[final["prioridad_enriquecimiento"] > 0].sort_values("prioridad_enriquecimiento", ascending=False)
    resumen_md += f"\n- Candidatas a enriquecer en la web (sin datos suficientes para calificar): {len(candidatos)}"
    candidatos[["razon_social", "localidad", "provincia", "dominio_email", "rubro_coi", "puntaje",
                "prioridad_enriquecimiento", "fuente"]].to_csv(salida / "candidatos_enriquecer.csv", sep=";", index=False)
    (salida / "resumen.md").write_text(f"# Resumen de la revisión\n\n{resumen_md}\n", encoding="utf-8")

    excel = salida / "trabajo.xlsx"
    borradores = final[final["categoria"].isin(["A", "B"])].rename(
        columns={"email": "contacto_email", "telefono": "contacto_telefono"})
    with pd.ExcelWriter(excel, engine="openpyxl") as xw:
        tabla_entrega.to_excel(xw, sheet_name="Entrega", index=False)
        borradores[["categoria", "puntaje", "razon_social", "nombre_fantasia", "contacto_nombre", "contacto_email",
                    "email_estado", "email_asunto", "borrador"]].to_excel(xw, sheet_name="Borradores", index=False)
        borradores[borradores["contacto_telefono"].notna()][
            ["categoria", "razon_social", "contacto_nombre", "contacto_telefono", "verificar_no_llame",
             "enlace_whatsapp", "guion_llamada"]].to_excel(xw, sheet_name="Telefono (chequear No Llame)", index=False)

    with seguimiento.conectar(_db(config)) as con:
        seguimiento.guardar_empresas(tabla_entrega, con)

    consola.print(resumen_md)
    consola.print(f"[green]Entrega:[/] {salida / 'entrega.csv'}\n[green]Trabajo:[/] {excel}\n"
                  f"[green]Resumen:[/] {salida / 'resumen.md'}")


def fuentes_disponibles() -> list[Path]:
    """Carteras de datos/entrada, enriquecimientos y respuestas CSV del canal."""
    entrada = [p for p in sorted((RAIZ / "datos/entrada").rglob("*"))
               if p.suffix.lower() in {".csv", ".xlsx", ".xls", ".pdf"}]
    return entrada + sorted((RAIZ / "canal/respuestas").glob("*.csv"))


@app.command()
def todo(
    verificar_mx: bool = typer.Option(True, "--verificar-mx/--sin-mx"),
    reiniciar: bool = typer.Option(False, "--reiniciar", help="Sobrescribe el seguimiento existente"),
    config_path: Path = OpcionConfig,
):
    """Procesa todas las fuentes disponibles: carteras, enriquecimientos y respuestas del canal."""
    procesar(fuentes_disponibles(), RAIZ / "datos/salida", verificar_mx, reiniciar, config_path)


@app.command()
def cola(limite: int = typer.Option(20), config_path: Path = OpcionConfig):
    """Siguientes empresas A/B a contactar."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        _tabla(seguimiento.cola(con, limite), "Cola de contacto")


@app.command()
def registrar(
    empresa_id: int = typer.Argument(..., help="ID de la empresa (ver 'cola')"),
    resultado: str = typer.Argument(..., help=" | ".join(seguimiento.RESULTADOS)),
    canal: str = typer.Option("email", help="email | llamada | whatsapp"),
    nota: str = typer.Option(""),
    proximo: str = typer.Option("", help="Próximo paso / fecha"),
    config_path: Path = OpcionConfig,
):
    """Registra un contacto. 'baja' y 'figura_no_llame' quedan en la lista de bajas para siempre."""
    config = _config(config_path)
    with seguimiento.conectar(_db(config)) as con:
        try:
            estado = seguimiento.registrar(con, empresa_id, canal, resultado, nota, proximo,
                                           _ruta(config, "bajas", "datos/bajas.csv"))
        except ValueError as e:
            consola.print(f"[red]{e}[/]")
            raise typer.Exit(1)
    consola.print(f"Empresa {empresa_id} -> [bold]{estado}[/]")


@app.command()
def resumen(config_path: Path = OpcionConfig):
    """Estado del pipeline por categoría."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        df = seguimiento.resumen(con)
    _tabla(df.pivot_table(index="categoria", columns="estado", values="empresas", aggfunc="sum",
                          fill_value=0).astype(int).reset_index(), "Pipeline")


@app.command()
def exportar(
    archivo: Path = typer.Option(RAIZ / "datos/salida/seguimiento.xlsx", "--archivo", "-o"),
    config_path: Path = OpcionConfig,
):
    """Exporta empresas con su estado e historial de contactos a Excel."""
    with seguimiento.conectar(_db(_config(config_path))) as con:
        empresas = pd.read_sql_query("SELECT * FROM empresas", con)
        historial = pd.read_sql_query(
            "SELECT i.*, COALESCE(e.nombre_fantasia, e.razon_social) AS empresa FROM interacciones i "
            "JOIN empresas e ON e.id = i.empresa_id ORDER BY i.fecha DESC", con)
    with pd.ExcelWriter(archivo, engine="openpyxl") as xw:
        empresas.to_excel(xw, sheet_name="Empresas", index=False)
        historial.to_excel(xw, sheet_name="Contactos", index=False)
    consola.print(f"[green]Exportado:[/] {archivo}")


if __name__ == "__main__":
    app()
