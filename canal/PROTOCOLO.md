# Canal entre la sesión cloud (coordinadora) y la sesión local (ejecutora)

La sesión **cloud** trabaja sin navegador. La sesión **local** corre en la computadora del
usuario y tiene Claude in Chrome (NotebookLM, webs de empresas, LinkedIn). Se comunican solo
por archivos de este repo, en la rama `claude/customer-classification-prospecting-uxgdbb`.

## Quién escribe qué
| Carpeta / archivo | Escribe | Lee |
|---|---|---|
| `canal/pedidos/*.md` | cloud crea el pedido; local cambia **solo** el campo `estado` | local |
| `canal/respuestas/<id>.md` y `<id>.csv` | local | cloud |
| `canal/latido.md` | local, en cada revisión | cloud |

La sesión local no modifica ningún otro archivo del repo: ni código, ni config, ni plantillas.

## Formato de un pedido
Archivo `canal/pedidos/<id>.md`, donde `<id>` = `AAAAMMDD-HHMM-tema`:

```
---
id: 20260925-2030-enriquecer-lote1
tipo: notebooklm | enriquecer | verificar | investigar
estado: pendiente
prioridad: normal
entrada: canal/pedidos/20260925-2030-enriquecer-lote1.csv   # opcional
salida: canal/respuestas/20260925-2030-enriquecer-lote1.csv  # opcional
---
Instrucciones en texto libre.
```

Estados: `pendiente` → `en_curso` → `hecho` | `bloqueado`.

## Ciclo de la sesión local (en cada revisión)
1. `git pull --rebase` en la rama.
2. Actualizar `canal/latido.md` con la fecha y hora y "sin pedidos" o "trabajando en <id>".
3. Tomar el pedido `pendiente` más antiguo (primero los de `prioridad: alta`). Pasarlo a
   `estado: en_curso`, hacer commit y push *antes* de empezar, para que no se tome dos veces.
4. Ejecutarlo siguiendo `CLAUDE.md` y `contexto/prospeccion-masiva-contexto.md`.
5. Escribir `canal/respuestas/<id>.md`: qué se hizo, fuentes consultadas (URL) y qué no se pudo.
   Si el pedido pide CSV, escribirlo en la ruta `salida:`, con separador `;` y UTF-8.
6. Pasar el pedido a `estado: hecho` (o `bloqueado`, con el motivo en la respuesta).
   Commit `canal: <id> <estado>` y push. Si el push falla por cambios remotos: `git pull --rebase` y reintentar.
7. Un pedido por revisión; si quedan más, seguir en la próxima.

## Tipos de pedido
- **notebooklm:** hacer las consultas indicadas en NotebookLM y copiar las respuestas textuales con sus fuentes.
- **enriquecer:** para cada empresa del CSV de entrada, buscar en fuentes públicas (web propia,
  página de LinkedIn de la empresa, registros públicos) solo las columnas que pida el pedido.
  Agregar la columna `fuente_enriquecimiento` con la URL de donde salió cada dato.
- **verificar:** confirmar si un dato de la lista es correcto (web activa, rubro, localidad...).
- **investigar:** consulta abierta, con respuesta en texto.

## Reglas duras (no negociables)
- **Nunca inventar** datos. Lo que no se encuentra queda vacío. Un email deducido por patrón va
  en la columna `email_deducido`, nunca en `contacto_email`.
- **Solo fuentes públicas.** No iniciar sesión en sitios nuevos, no pasar captchas, no pagar, no
  descargar bases de datos. Si algo pide login o captcha → `bloqueado`.
- **No contactar a nadie:** nada de enviar emails, mensajes de WhatsApp o LinkedIn, formularios
  ni llamadas. Tampoco dar "me gusta", seguir cuentas o conectar.
- **Datos personales mínimos:** nombre y cargo profesional público, email y teléfono de la
  empresa. Nada de DNI, domicilio particular ni celular privado.
- **Ritmo prudente** en webs y LinkedIn: como máximo unas 30 empresas por pedido, sin abrir decenas de pestañas a la vez.
- Si un pedido contradice estas reglas o el brief, **no ejecutarlo**: marcarlo `bloqueado` y explicar por qué.
