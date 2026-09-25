# Clientes – clasificación, cualificación y prospección

Kit en Python para procesar listas grandes de clientes y preparar la prospección
(llamadas, WhatsApp y email) para ofrecer un sistema.

## Qué hace

1. **Importa** uno o varios CSV/Excel (detecta separador y reconoce columnas con distintos nombres: `Teléfono`, `movil`, `celular`...).
2. **Limpia**: teléfonos a formato internacional (E.164) y validados, emails validados, nombres normalizados, cifras como `1,2M`, `80k` o `10-20` convertidas a número.
3. **Deduplica**: por teléfono, email o nombre+empresa parecidos (fuzzy), fusionando los datos de los duplicados.
4. **Puntúa (0-100) y segmenta** en A / B / C según reglas de `config.yaml` (sector, tamaño, facturación, datos de contacto, zona, señales de interés). Guarda los *motivos* de cada puntuación.
5. **Asigna canal**: A → llamada, B → WhatsApp, C → email (si falta el dato, usa otro canal).
6. **Genera mensajes personalizados**: texto y enlace `wa.me` de WhatsApp listo para pulsar, email con asunto y guion de llamada con preguntas de cualificación (plantillas en `plantillas/`).
7. **Seguimiento**: base SQLite con cola de contacto priorizada, registro de resultados y estado del pipeline.

## Instalación

```bash
./instalar.sh
source .venv/bin/activate
```

## Uso

```bash
# 1. Ajusta config.yaml: país, sectores objetivo, umbrales y datos de tu oferta
# 2. Deja tus archivos en datos/entrada/ (no se suben a git) y procesa todos a la vez
python -m prospeccion procesar datos/entrada/*.csv datos/entrada/*.xlsx

# Resultado: datos/salida/clientes_clasificados.xlsx con hojas
#   Todos | Segmento A/B/C | Llamadas | WhatsApp | Email | Sin contacto

# 3. Siguientes clientes a contactar
python -m prospeccion cola --canal llamada --limite 30

# 4. Registrar el resultado de cada contacto
python -m prospeccion registrar 12 interesado --nota "Pide demo" --proximo "martes 10h"
python -m prospeccion registrar 15 buzon --canal whatsapp

# 5. Ver el pipeline y exportar el seguimiento a Excel
python -m prospeccion resumen
python -m prospeccion exportar
```

Resultados posibles de `registrar`: `sin_respuesta`, `buzon`, `interesado`, `no_interesado`,
`volver_a_llamar`, `reunion`, `numero_erroneo`. Un cliente sale de la cola tras 4 intentos
o cuando pasa a interesado / reunión / perdido / no contactar.

Si vuelves a ejecutar `procesar` con registros ya hechos, se detiene para no perder el
historial: primero `exportar`, luego `procesar ... --reiniciar`.

Prueba con los datos de ejemplo: `python -m prospeccion procesar datos/ejemplo_clientes.csv`.

## Personalizar

- `config.yaml`: columnas, reglas de puntuación, umbrales A/B/C, canal por segmento y datos de tu oferta.
- `plantillas/*.j2`: textos de WhatsApp, email y guion de llamada (Jinja2; puedes usar cualquier columna, p. ej. `{{ empresa }}`, `{{ ciudad }}`, `{{ segmento }}`).

## Aviso legal

Antes de contactar en frío, revisa la normativa de tu país (en la UE: RGPD y LSSI; listas
Robinson; en otros países, sus registros de exclusión). Respeta a quien pide no ser
contactado: registra `numero_erroneo` o marca el estado `no_contactar`.

## Tests

```bash
python -m pytest -q
```
