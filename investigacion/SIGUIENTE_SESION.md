# Cómo seguir en una sesión nueva

Estado al 2026-09-28 por la noche: tandas t2 a t9, rebúsquedas r1-r3 y pasadas rápidas q1-q2 hechas; el
tablero tiene 475 empresas; `todo` y `cartera` corridos sobre las carteras completas (17.660 empresas: 5 A,
213 B, 500 descartadas). **La rama con el estado actual es `claude/exciting-shannon-5osp3h`** (las ramas
`claude/adoring-faraday-ko05j5` y `claude/customer-classification-prospecting-uxgdbb` quedaron atrás).
Leé también `CLAUDE.md` y `contexto/prospeccion-masiva-contexto.md`.

**Desde el 28-09 el trabajo sigue en la sesión local** (Claude Code en la computadora del usuario, con
Claude in Chrome). La sección siguiente es para esa sesión; el resto del documento describe el ciclo tal
como se corría en la nube y sigue valiendo, con las diferencias que se marcan.

## Estado al 2026-09-29 (sesión local)
Las rondas 12 a 15 están hechas (ver el historial en `canal/respuestas/20260926-1200-verificar-AB.md`). El
tablero tiene 496 empresas y 263 listas (174 de las 231 A/B); la entrega, 8 A y 224 B. La cloud se quedó sin
tokens: el trabajo sigue solo en la sesión local.
- **Todas las A/B con alerta pasaron por una revisión web** (alerta1 y alerta2) y todas las A/B sin decisor o sin
  canal por una rebúsqueda (r1 a r5). Lo que falta ya no sale de webs: queda para LinkedIn.
- **Codificación:** los scripts que leen `config.yaml` tienen que abrirlo con `encoding="utf-8"`; en Windows,
  sin eso, los borradores salen con las tildes rotas.
- **Antes de republicar el tablero**, correr `investigacion/herramientas/control_calidad.py`. Revisa emails que
  rebotarían, teléfonos sin «No Llame», borradores sin COI o sin baja, y decisores con dato viejo.
- Rondas 12 a 15 hechas. El tablero tiene 263 empresas listas (174 de las 231 A/B).
- **Nuevo:** `elegir_ab.py` elige las A/B de la entrega sin investigación completa (las que confirma la pasada
  rápida). `elegir_tanda.py` las salteaba. `sumar_revision.py` aplica las salidas de `instrucciones_revision.md`,
  que resuelven alertas del tablero.
- **Decisiones del usuario (29-09):** las constructoras (obra civil, vial, pública y de edificios) entran como
  prospecto, y también los fabricantes que venden a cadenas (Crivel).
- **Ritmo pedido por el usuario:** 3 agentes a la vez; WebFetch de a una página y como máximo 3 por sitio;
  LinkedIn solo desde la sesión principal, con 10-15 s entre páginas y unas 30 páginas por día.
- **Pasadas rápidas q4 a q10 hechas (29-09).** El rendimiento de B cayó de ~12 % (q4-q5) a ~2,5 % (q7-q10).
  **El usuario decidió frenarlas** y dejar contactables las B que ya hay. Quedan unas 1.176
  «industrial_otro» y 4.523 «indeterminado» sin pasar; no se retoman sin que el usuario lo pida.
- **Próximo:**
  1. LinkedIn con `investigacion/pendientes_linkedin.md`: B sin decisor o sin canal y tamaños por confirmar.
     Como máximo unas 30 páginas por día.
  2. Resolver las B con alerta que siguen en duda y mantener el tablero publicado al día.

## Para la sesión local (Windows, Claude in Chrome)

### Qué cambia respecto de la nube
- **Podés abrir las páginas.** En la nube la red bloqueaba las webs de empresas y LinkedIn, y todo salió de
  resúmenes de buscador («según buscador» en las notas). Acá abrí la web real, su página de contacto y la
  página pública de LinkedIn de la empresa. Los archivos `investigacion/herramientas/instrucciones_*.md`
  dicen «solo WebSearch, WebFetch bloqueado» por ese proxy: **acá WebFetch y Chrome están permitidos**; el
  resto de esas instrucciones (fuentes válidas, columnas, tope de búsquedas, nada de ZoomInfo/RocketReach/
  ContactOut, no inventar) se mantiene igual.
- **Chrome lo maneja la conversación principal**, no los subagentes. Repartí las tandas entre subagentes con
  WebSearch y WebFetch, y usá Chrome vos para lo que WebFetch no pueda leer (LinkedIn, páginas con JavaScript).
- **Solo lectura:** no iniciar sesión en sitios nuevos, no pasar captchas, no escribir en formularios, no
  contactar a nadie, no seguir ni conectar en LinkedIn (reglas de `canal/PROTOCOLO.md`).
- **Ritmo prudente** en webs y LinkedIn: de a una pestaña, sin abrir decenas a la vez.

### Puesta en marcha
```powershell
git fetch origin
git checkout claude/exciting-shannon-5osp3h
git pull
python -m venv .venv
.venv\Scripts\activate            # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # 18 tests
$env:PYTHONPATH = "."               # en cmd: set PYTHONPATH=.   | en Linux/Mac: export PYTHONPATH=.
python investigacion/herramientas/sumar_triaje.py     # regenera datos/entrada/triaje.csv (no está en git)
python -m prospeccion todo
python -m prospeccion cartera
```
`todo` tarda uno o dos minutos (chequea los registros MX de unos 2.000 dominios). Deja `datos/salida/entrega.csv`,
`trabajo.xlsx`, `resumen.md`, `candidatos_enriquecer.csv` y `cartera_unificada.csv/.xlsx`; nada de eso se sube a git.

### Antes de cada `todo`: traer los estados del tablero
El tablero publicado (https://claude.ai/artifact/GWHPMBCqFmjVfFoLL8h3u5) guarda en su base qué pasó con cada
contacto. Para que el seguimiento y las bajas lo reflejen:
1. En la página, botón **«Exportar estados (CSV)»** y guardalo como `datos/salida/estados_tablero.csv`
   (columnas `razon_social;localidad;categoria;estado;canal;quien;fecha;nota`). Si la sesión tiene la
   herramienta ArtifactData, también podés leer la colección `contactos` de ese artefacto y escribir el CSV vos.
2. `python -m prospeccion importar-estados` (después de un `todo`, porque necesita la lista de empresas).
   Las bajas y los «No Llame» quedan en `datos/bajas.csv` para siempre. Al 28-09 a la noche la base estaba vacía.

### Qué hacer, en orden de rendimiento
1. **Revisar las 119 «a revisar» del tablero** (alerta cargada por los agentes: grupo grande, posible minorista,
   homónimo, dato viejo). Abrí la web y decidí. Lo que se descarte o se rescate va a `datos/revisiones.csv`
   (`razon_social;decision;motivo`, decisión `mantener` o `descartar`), que manda sobre las reglas. Después `todo`.
2. **Rebúsqueda r4:** 194 investigadas sin decisor o sin canal (7 ya pasaron por r3 sin resultado y el selector
   las saltea). Acá rinde mucho más que en la nube porque podés abrir «Contacto» y LinkedIn.
   ```powershell
   python investigacion/herramientas/elegir_rebusca.py r4 96 8      # investigacion/tandas/r4_1.csv ... r4_8.csv
   ```
   Un subagente por archivo: «Leé `investigacion/herramientas/instrucciones_rebusca.md` y seguilas al pie de la
   letra; además podés abrir las webs con WebFetch. Entrada (con encabezado): `investigacion/tandas/r4_i.csv`.
   Salida: `investigacion/tandas/r4_outi.csv`». Lo que los subagentes no pudieron leer, abrilo vos con Chrome y
   completá la fila. Después, **una sola vez por tanda**:
   ```powershell
   python investigacion/herramientas/completar.py "r4_out*.csv"     # solo rellena vacíos con datos que traen URL
   ```
3. **Pasada rápida q3** (nivel 3 del embudo): quedan 1.567 del triaje sin rubro confirmado.
   ```powershell
   python investigacion/herramientas/elegir_rapida.py q3 240 8      # q3_1.csv ... q3_8.csv
   ```
   Subagentes con `instrucciones_rapida.md` (2 búsquedas o una visita a la web por empresa; acá abrir la
   web cuenta como la búsqueda que confirma). Luego `sumar_rapida.py "q3_out*.csv"`, `todo`, y anotá en
   `datos/revisiones.csv` las alertas que las reglas no toman. Repetir con q4, q5... hasta agotar.
4. **Tanda t10** (investigación completa): 126 candidatas con rubro detectado, casi todas de la cartera RAI sin
   localidad. En la nube dos de cada tres no se pudieron identificar; con Chrome se puede probar mejor
   (`elegir_tanda.py t10 96 8`, `instrucciones_agente.md`, `sumar.py "t10_out*.csv"`). Antes de lanzarla mirá la
   lista y sacá grandes y entes públicos en `datos/revisiones.csv`.
5. **NotebookLM** (`investigacion/pedido-notebooklm.md`): sigue pendiente desde el 25-09. Hace falta darle a la
   extensión de Chrome permiso sobre `notebooklm.google.com`. La respuesta va en `investigacion/notebooklm.md`.

### Cierre de cada ronda
```powershell
python -m prospeccion todo
python -m prospeccion cartera
python -m prospeccion tablero -o datos/salida/tablero.html
```
- **Publicar el tablero:** si la sesión tiene la herramienta Artifact, leé primero el artefacto publicado
  (`read` con la URL de arriba) y republicá `datos/salida/tablero.html` pasando esa misma `url`, para no perder
  los estados guardados. Si no la tiene, pedile a una sesión en la nube que lo publique: abrir el HTML como
  archivo local funciona para mirar, pero ahí los estados no se guardan.
- Anotá la ronda en `canal/respuestas/20260926-1200-verificar-AB.md` (es el historial), y hacé commit y push a
  `claude/exciting-shannon-5osp3h`. Entran a git las salidas de los agentes (`investigacion/tandas/`), el CSV de
  prospectos, `datos/revisiones.csv` y las notas; **no** entran `datos/salida/`, `datos/bajas.csv` ni
  `datos/entrada/triaje.csv` (ignorados).

### Reglas que no cambian
Nunca inventar ni deducir emails, teléfonos ni nombres: sin URL, vacío. Del Boletín Oficial solo nombre y cargo.
Nada de ZoomInfo, RocketReach, ContactOut, Lusha ni Apollo. Todo teléfono lleva `verificar_no_llame = sí`. Todo
borrador identifica a COI y termina con la línea de baja; una baja no se borra nunca. No se envía nada desde acá.
**Falta definir** el remitente de los borradores: hoy sale «[tu nombre]» (`config.yaml` → `oferta.remitente`).


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
PYTHONPATH=. python investigacion/herramientas/elegir_tanda.py t10 96 8
```
1. Lanzá 8 agentes en paralelo con este prompt, cambiando `i`:
   «Leé las instrucciones en investigacion/herramientas/instrucciones_agente.md y seguilas al pie
   de la letra. Entrada (sin encabezado): investigacion/tandas/t10_i.csv. Salida:
   investigacion/tandas/t10_outi.csv». Usá rutas absolutas del repo.
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
Quedan 126 candidatas con rubro detectado en `candidatos_enriquecer.csv` (tanda t10), casi todas nombres de la
cartera RAI sin localidad: en la t9 dos de cada tres no se pudieron identificar. Rinden más la pasada rápida q3 y
la rebúsqueda r4. Antes de lanzar una tanda,
mirá la lista: la cola trae grandes y entes públicos que las reglas no toman; anotalos en `datos/revisiones.csv` y
volvé a correr `todo` y `elegir_tanda.py`. Las 1.567 del triaje sin rubro siguen por la pasada rápida (q3, q4...).
