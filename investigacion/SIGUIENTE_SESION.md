# Cómo seguir en una sesión nueva

Estado al 2026-09-28 (tandas t2 a t8, rebúsquedas r1-r3 y pasadas rápidas q1-q2 hechas; las próximas son t9, q3 y r4). Leé también `CLAUDE.md` y `contexto/prospeccion-masiva-contexto.md`.

## Dónde está todo
- **Listas originales:** `datos/entrada/` (carteras RAI y AG-360 de F. Dabbene y 3 PDF de zonas).
  El usuario pidió subirlas a git, aunque el repo es público.
- **Prospectos investigados:** `canal/respuestas/20260926-prospectos-AB.csv`. Tiene 396 empresas o
  más, con decisor, canal, gancho (`dato`), `alerta`, `nota` y borrador. Es la fuente del tablero.
- **Historial de rondas y descartes:** `canal/respuestas/20260926-1200-verificar-AB.md`.
- **Revisión manual:** `datos/revisiones.csv` (`razon_social;decision;motivo`, decisión `mantener` o `descartar`).
  Manda sobre las reglas automáticas y se sube a git; la aplican `todo`/`procesar` y `sumar.py`. Usalo para los descartes que las reglas no toman (grupo
  grande, UTE, gomerías) y para revertir falsos descartes (p. ej. «tienda online» o una localidad que coincide
  con una marca grande).
- **Tandas ya investigadas:** `investigacion/tandas/` (`tN_i.csv` = entrada, `tN_out*.csv` = salida
  de los agentes). `elegir_tanda.py` las lee para no repetir empresas.
- **Cartera unificada:** `datos/salida/cartera_unificada.csv` y `.xlsx` (`python -m prospeccion cartera`).
  Una fila por empresa de las tres carteras, con el contacto **de origen** (como vino en la cartera, sin
  verificar) separado del **verificado** (con URL y fecha), y el rubro con su estado: `verificado` (lo
  describió la investigación), `por nombre (sin verificar)` (palabras del nombre) o `sin dato`. Nada se deduce.
- **Tablero publicado:** https://claude.ai/artifact/GWHPMBCqFmjVfFoLL8h3u5. Para actualizarlo desde
  otra sesión, publicá pasando esa URL como `url` en la herramienta Artifact (leelo primero con `read`).
  Desde 2026-09-28 es una lista de trabajo con estado por empresa, guardado en la base del artefacto
  (capacidades `db` y `downloads`, colección `contactos`, un documento por empresa con `estado`, `quien`, `fecha`,
  `nota`, `canal` e `historial`). **Antes de cada `todo`**, traé esos estados al repo: leé la colección con la
  herramienta ArtifactData (`list` sobre `contactos`), escribí `datos/salida/estados_tablero.csv`
  (`razon_social;localidad;categoria;estado;canal;quien;fecha;nota`) y corré `python -m prospeccion importar-estados`.
  Las bajas y los «No Llame» quedan en `datos/bajas.csv` y `todo` los descarta para siempre. El usuario también
  puede bajar ese CSV desde el botón «Exportar estados» de la página.

## Ciclo de una tanda (unas 96 empresas, 8 agentes de 12)
```bash
./instalar.sh && source .venv/bin/activate
python -m prospeccion todo                      # recalcula datos/salida/candidatos_enriquecer.csv
PYTHONPATH=. python investigacion/herramientas/elegir_tanda.py t8 96 8
```
1. Lanzá 8 agentes en paralelo con este prompt, cambiando `i`:
   «Leé las instrucciones en investigacion/herramientas/instrucciones_agente.md y seguilas al pie
   de la letra. Entrada (sin encabezado): investigacion/tandas/t8_i.csv. Salida:
   investigacion/tandas/t8_outi.csv». Usá rutas absolutas del repo.
2. Cuando terminen, revisá que cada salida tenga 17 columnas en todas las filas y corré:
   `PYTHONPATH=. python investigacion/herramientas/sumar.py "t6_out*.csv"`
   El script califica con `config.yaml`, arma el borrador y suma al CSV de prospectos. Lista las
   descartadas.
3. Revisá las descartadas: la regla de consumidor final puede fallar. Por ejemplo, Metalúrgica
   Andi fabrica máquinas para carnicerías y cayó como B2C. Sacá del CSV las que tengan una alerta
   clara de cierre, quiebra o servicio público.
4. Regenerá y publicá el tablero:
   `python -m prospeccion tablero -o <scratchpad>/tablero.html`, y publicalo con Artifact.
5. Regenerá la entrega y la cartera unificada: `python -m prospeccion todo && python -m prospeccion cartera`.
6. Anotá la ronda en `canal/respuestas/20260926-1200-verificar-AB.md`, hacé commit y push.

## Rebúsqueda (segunda pasada a las investigadas con datos faltantes)
```bash
PYTHONPATH=. python investigacion/herramientas/elegir_rebusca.py r4 96 8
```
Lanzá 8 agentes con: «Leé las instrucciones en investigacion/herramientas/instrucciones_rebusca.md y seguilas al
pie de la letra. Entrada (con encabezado): investigacion/tandas/r4_i.csv. Salida: investigacion/tandas/r4_outi.csv».
Después: `PYTHONPATH=. python investigacion/herramientas/completar.py "r4_out*.csv"`. Solo rellena vacíos con
datos que traen URL; nunca pisa lo que ya estaba. **Corrélo una sola vez por tanda:** una segunda corrida vuelve a
pegar las notas de rebúsqueda. Luego `todo`, `cartera`, tablero, commit. Quedan 194 investigadas con algún dato
faltante; las 7 que ya pasaron por r3 sin resultado no se repiten.

## Límites y reglas
- **Red:** WebFetch está bloqueado para las webs de empresas y solo funciona WebSearch.
- **Búsquedas:** hay un tope de 1500 por sesión. Cada tanda gasta unas 300 o 350.
- **Datos:** nunca inventar ni deducir emails. No usar ZoomInfo, RocketReach ni sitios parecidos.
  Del Boletín Oficial se toman solo nombre y cargo.
- **Borradores:** todo teléfono lleva `verificar_no_llame = sí` y todo borrador termina con la línea
  de baja. Son reglas del brief y se mantienen.
- **Falta definir:** el remitente de los borradores. Hoy sale «[tu nombre]», en `config.yaml` →
  `oferta.remitente`.

## Estrategia para las 16.700 sin rubro
Leé `investigacion/ESTRATEGIA_16700.md`: embudo de 5 niveles (personas físicas afuera → triaje por nombre con
haiku → pasada rápida de rubro con 2 búsquedas → investigación completa solo de las que encajan → rebúsqueda).
Herramientas: `armar_triaje.py` / `sumar_triaje.py`, `elegir_rapida.py` / `sumar_rapida.py`.
**El triaje ya está hecho** (`datos/entrada/triaje.csv` se regenera con `sumar_triaje.py` desde `investigacion/triaje/`,
9.211 empresas). Pasadas rápidas hechas: q1 (48) y q2 (240). Lo que sigue: `elegir_rapida.py q3 240 8`
(quedan 1.567), 8 agentes sonnet con `instrucciones_rapida.md`, `sumar_rapida.py "q3_out*.csv"`, `todo`, `cartera`.
Después de sumar, revisá las alertas que las reglas no descartaron (grupo grande, UTE, «posible minorista») y
anotá las decisiones en `datos/revisiones.csv`.

## Qué queda
Quedan 174 candidatas con rubro detectado en `candidatos_enriquecer.csv` (tanda t9). Antes de lanzar una tanda,
mirá la lista: la cola trae grandes y entes públicos que las reglas no toman; anotalos en `datos/revisiones.csv` y
volvé a correr `todo` y `elegir_tanda.py`. Las 1.567 del triaje sin rubro siguen por la pasada rápida (q3, q4...).
