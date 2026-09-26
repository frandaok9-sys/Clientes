# Clientes: prospección masiva para COI

Kit en Python que toma listas de empresas (bases compradas, cámaras, directorios o carteras) y las
deja listas para prospectar **COI**, siguiendo el brief `contexto/prospeccion-masiva-contexto.md`.
Las reglas para agentes están en `CLAUDE.md`.

## Qué hace
1. **Importa** varios CSV o Excel y reconoce columnas con distintos nombres. Registra la `fuente` de cada fila.
2. **Limpia:** valida el CUIT (dígito verificador), pasa los teléfonos argentinos a E.164, valida emails y normaliza el dominio web.
3. **Deduplica** por CUIT, por dominio web o por razón social normalizada (sin SRL/SA) más localidad.
4. **Califica** con el puntaje del brief (rubro, tamaño, área comercial, obras en campo, USD/minería, crecimiento, Google Workspace, decisor) y asigna **A ≥ 10**, **B 6–9**, **C ≤ 5**.
5. **Madurez digital:** `alta` (web y correo de dominio propio), `media` (una de las dos) o `baja` (ninguna).
   Las de madurez baja no se descartan: suelen manejarse con papel, planillas y WhatsApp, y se prospectan
   por teléfono. Van en la hoja «Poco digitalizadas» del Excel.
6. **Descarta con motivo:** fuera de Argentina, B2C, grandes empresas con ERP, competidores, clientes actuales y bajas. Las unipersonales quedan como `C - chico`; sin dominio propio, `requiere_dominio = sí`.
7. **Google Workspace:** con `--verificar-mx`, consulta los registros MX del dominio.
8. **Borradores** para A y B en voseo, de 90 palabras como máximo, con la línea de baja, y un guion de llamada con el aviso del Registro «No Llame».
9. **Seguimiento:** cola de contacto y registro de resultados. Una `baja` se guarda para siempre en `datos/bajas.csv`.

No envía mensajes ni hace llamadas: prepara la lista y los borradores para que los mande una persona.

## Formatos de cartera reconocidos
Además de CSV/Excel con encabezados, `procesar` detecta solo estos formatos:
- **RAI:** exportación de CRM con "Nombre completo", "Correo electrónico", "Vendedor"...
- **AG-360:** planilla por zonas sin encabezados (nombre, CUIT, código, localidad, contacto, email, teléfonos).
- **PDF de zonas:** listados de clientes (Id, Cliente, Región, Ciudad...), aunque el texto venga superpuesto.

Los nombres en formato "Apellido, Nombre" y los CUIT 20/23/24/27 se tratan como personas físicas
(`C - chico`). Los emails repetidos en 3 o más empresas se descartan porque son comodines de carga.
Las marcas internas como "Prejudicial" se quitan del nombre.

## Enriquecimiento
Si la lista no trae tamaño ni señales, casi todo queda en C. `procesar` genera
`datos/salida/candidatos_enriquecer.csv`, ordenado por potencial. Los lotes se mandan a la sesión
local (con navegador) por `canal/`, y su CSV de respuesta se vuelve a procesar como una entrada más:
se une a la empresa por razón social y localidad, y completa los datos que faltan.

## Uso
```bash
./instalar.sh && source .venv/bin/activate
python -m prospeccion todo          # todas las fuentes: carteras + enriquecimientos + canal/respuestas
python -m prospeccion procesar datos/entrada/*.csv datos/entrada/*.xlsx --verificar-mx
#   datos/salida/entrega.csv  -> formato de la sección 8 (UTF-8, separador ;)
#   datos/salida/resumen.md   -> filas, duplicados, A/B/C, descartes por motivo y top 3 rubros
#   datos/salida/trabajo.xlsx -> Entrega | Borradores | Teléfono (chequear No Llame)
python -m prospeccion tablero      # datos/salida/tablero.html: prospectos por carril (decisor y canal, solo canal, sin canal, revisar)
python -m prospeccion cola
python -m prospeccion registrar 3 demo_agendada --nota "jueves 10h"
python -m prospeccion registrar 5 baja          # queda en datos/bajas.csv para siempre
python -m prospeccion resumen
python -m prospeccion exportar
```
Resultados posibles: `sin_respuesta`, `buzon`, `interesado`, `no_interesado`, `volver_a_llamar`,
`demo_agendada`, `numero_erroneo`, `figura_no_llame`, `baja`.

## Personalizar
- `config.yaml`: rubros (palabras, dolor, solución, plan), puntajes, señales, descartes, clientes actuales, remitente.
- `plantillas/*.j2`: textos de WhatsApp/email y guion de llamada.

## Pendiente de definir (brief, sección 7)
- **Remitente de los borradores:** hoy sale `[tu nombre]`.
- **`email_estado`:** el brief admite `verificado`, `deducido` o `generico`. Un email personal que viene en la lista y nadie verificó se marca `sin_verificar`, para no darlo por verificado.
- **`usuarios_probables`:** queda vacío porque no se estima sin datos.
- **Enriquecimiento web** (sitio propio, LinkedIn): todavía no está automatizado.

## Tests
```bash
python -m pytest -q
```
