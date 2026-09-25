# Proyecto: prospección masiva para COI

Este repo prepara listas de empresas para la prospección comercial de **COI (Centro
Operativo Industrial)**, CRM-ERP en la nube para PyMEs industriales argentinas.

**Fuente de verdad del negocio:** `contexto/prospeccion-masiva-contexto.md`. Leelo antes de
calificar listas, escribir borradores o cambiar reglas. Si algo de acá contradice ese brief,
manda el brief.

## Reglas que no se rompen
- Nunca inventar emails, teléfonos, nombres ni datos de empresa. Lo no verificado queda vacío;
  un email deducido va marcado `deducido` y no se usa sin verificar.
- No se envían mensajes ni se hacen llamadas desde acá: solo lista + borradores.
- Todo teléfono lleva `verificar_no_llame = sí` (Registro «No Llame», Ley 26.951).
- Todo borrador identifica a COI y termina con la línea de baja. Las bajas
  (`datos/bajas.csv`) se respetan para siempre y nunca se borran.
- No dar precios, no nombrar clientes de COI, no prometer integración AFIP/ARCA ni WhatsApp integrado.
- Cada fila conserva su `fuente`.

## Dónde está cada cosa
- `config.yaml`: rubros, puntajes, descartes, clientes actuales y competidores (reglas del brief, secciones 3–5).
- `canal/`: pedidos a la sesión local (con Chrome) y sus respuestas. Protocolo en `canal/PROTOCOLO.md`.
- `prospeccion/`: limpieza, deduplicación, calificación, borradores y seguimiento.
- `plantillas/`: borradores en voseo (brief, sección 9).
- `datos/entrada/`: listas reales (no se suben a git). `datos/salida/`: resultados.

## Uso
```bash
./instalar.sh && source .venv/bin/activate
python -m prospeccion procesar datos/entrada/*.csv --verificar-mx
python -m pytest -q
```
