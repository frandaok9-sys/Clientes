# Cómo seguir en una sesión nueva

Estado al 2026-09-26. Leé también `CLAUDE.md` y `contexto/prospeccion-masiva-contexto.md`.

## Dónde está todo
- **Listas originales:** `datos/entrada/` (carteras RAI y AG-360 de F. Dabbene y 3 PDF de zonas).
  El usuario pidió subirlas a git, aunque el repo es público.
- **Prospectos investigados:** `canal/respuestas/20260926-prospectos-AB.csv`. Tiene 249 empresas o
  más, con decisor, canal, gancho (`dato`), `alerta`, `nota` y borrador. Es la fuente del tablero.
- **Historial de rondas y descartes:** `canal/respuestas/20260926-1200-verificar-AB.md`.
- **Tandas ya investigadas:** `investigacion/tandas/` (`tN_i.csv` = entrada, `tN_out*.csv` = salida
  de los agentes). `elegir_tanda.py` las lee para no repetir empresas.
- **Tablero publicado:** https://claude.ai/artifact/GWHPMBCqFmjVfFoLL8h3u5. Para actualizarlo desde
  otra sesión, publicá pasando esa URL como `url` en la herramienta Artifact.

## Ciclo de una tanda (unas 96 empresas, 8 agentes de 12)
```bash
./instalar.sh && source .venv/bin/activate
python -m prospeccion todo                      # recalcula datos/salida/candidatos_enriquecer.csv
PYTHONPATH=. python investigacion/herramientas/elegir_tanda.py t5 96 8
```
1. Lanzá 8 agentes en paralelo con este prompt, cambiando `i`:
   «Leé las instrucciones en investigacion/herramientas/instrucciones_agente.md y seguilas al pie
   de la letra. Entrada (sin encabezado): investigacion/tandas/t5_i.csv. Salida:
   investigacion/tandas/t5_outi.csv». Usá rutas absolutas del repo.
2. Cuando terminen, revisá que cada salida tenga 17 columnas en todas las filas y corré:
   `PYTHONPATH=. python investigacion/herramientas/sumar.py "t5_out*.csv"`
   El script califica con `config.yaml`, arma el borrador y suma al CSV de prospectos. Lista las
   descartadas.
3. Revisá las descartadas: la regla de consumidor final puede fallar. Por ejemplo, Metalúrgica
   Andi fabrica máquinas para carnicerías y cayó como B2C. Sacá del CSV las que tengan una alerta
   clara de cierre, quiebra o servicio público.
4. Regenerá y publicá el tablero:
   `python -m prospeccion tablero -o <scratchpad>/tablero.html`, y publicalo con Artifact.
5. Anotá la ronda en `canal/respuestas/20260926-1200-verificar-AB.md`, hacé commit y push.

## Límites y reglas
- **Red:** WebFetch está bloqueado para las webs de empresas y solo funciona WebSearch.
- **Búsquedas:** hay un tope de 1500 por sesión. Cada tanda gasta unas 300 o 350.
- **Datos:** nunca inventar ni deducir emails. No usar ZoomInfo, RocketReach ni sitios parecidos.
  Del Boletín Oficial se toman solo nombre y cargo.
- **Borradores:** todo teléfono lleva `verificar_no_llame = sí` y todo borrador termina con la línea
  de baja. Son reglas del brief y se mantienen.
- **Falta definir:** el remitente de los borradores. Hoy sale «[tu nombre]», en `config.yaml` →
  `oferta.remitente`.

## Qué queda
Quedan unas 525 candidatas con rubro detectado en `candidatos_enriquecer.csv`. Después vienen unas
6.700 sin rubro detectado, que conviene triar por nombre antes de gastar búsquedas.
