# Estrategia para prospectar las 16.700 sin rubro gastando lo mínimo

Estado al 2026-09-27. La cartera unificada tiene 17.661 empresas; 366 investigadas a fondo y 593 con rubro
solo por el nombre. Las otras **16.308 no tienen ningún dato de rubro** y las carteras no lo traen.

## Por qué no se puede investigar todo a fondo
Una investigación completa (existe, qué hace, decisor, canal, gancho) cuesta **unos 9.000 tokens y 3,5
búsquedas por empresa**. Para 16.300 empresas serían ~150 millones de tokens y ~57.000 búsquedas (38 sesiones
al tope de 1.500). No tiene sentido: la mayoría no es cliente de COI.

## Lo que ya se sabe sin gastar nada
De las 16.308 sin rubro y pendientes:
- **7.093 son personas físicas** (CUIT 20/23/24/27 o «Apellido, Nombre»): productores, monotributistas,
  clientes de mostrador. No son PyME industrial: quedan como `C - chico`, no se investigan.
- **9.215 son empresas.** De esas, 6.090 no traen ni email, ni teléfono, ni web (solo nombre);
  1.342 traen email con dominio propio (señal fuerte de empresa real y organizada); 1.438 traen teléfono.

## El embudo (cada nivel filtra antes de pagar el siguiente)

| Nivel | Qué hace | Quién | Costo por empresa | Universo | Total estimado |
|---|---|---|---|---|---|
| 0 | Excluir personas físicas y entidades no empresa (reglas locales) | Python | 0 | 16.308 → 9.215 | 0 |
| 1 | Ordenar por señal: dominio propio > teléfono > localidad | Python | 0 | 9.215 | 0 |
| 2 | **Triaje por nombre**: 4 clases, sin buscar en la web | haiku, lotes de 250 | ~80 tokens | 9.215 | ~0,8 M tokens, 0 búsquedas |
| 3 | **Pasada rápida de rubro**: existe, qué hace, tamaño, descarte. 2 búsquedas máx. | sonnet, 30 por agente | ~2.500 tokens, 2 búsquedas | industrial_objetivo + industrial_otro (est. 2.500–3.500) | ~8 M tokens, ~6.000 búsquedas (4 sesiones) |
| 4 | **Investigación completa** (decisor, canal, gancho, borrador) | sonnet, 12 por agente | ~9.000 tokens, 3,5 búsquedas | las que pasan el nivel 3 con rubro prioritario y tamaño PyME (est. 700–1.000) | ~9 M tokens, ~3.500 búsquedas (3 sesiones) |
| 5 | **Rebúsqueda** de decisor o canal faltante | sonnet | ~9.500 tokens, 4 búsquedas | ~40 % de las investigadas | ~4 M tokens, ~1.500 búsquedas |

**Total estimado: ~22 M tokens y ~11.000 búsquedas (8 sesiones)**, contra ~150 M tokens por fuerza bruta.
El triaje por nombre es la palanca: decide en qué 3.000 empresas gastar búsquedas.

## Reglas que no cambian con el embudo
- El **triaje no es un dato de la empresa**: solo ordena la cola. Nunca aparece como rubro ni se muestra al usuario
  como característica de la empresa. En la cartera el rubro sigue siendo `sin dato` hasta que una fuente lo confirme.
- La **pasada rápida** confirma rubro con URL. Entra a la cartera como `verificado (pasada rápida)` y a la entrega
  como `rubro` informado (manda sobre el nombre). Una alerta de descarte descarta por las reglas de `config.yaml`.
- Nada se deduce: sin URL, la fila queda vacía. Un email deducido nunca entra. Todo teléfono lleva `verificar_no_llame = sí`.
- Ante la duda, el triaje elige `indeterminado` antes que `no_objetivo`: descartar por nombre es peor que investigar de más.

## Cómo ahorrar tokens dentro de cada nivel
1. **Modelo por nivel:** haiku para clasificar nombres, sonnet para buscar. La ronda t7/r2 se hizo con sonnet
   para comparar: misma disciplina de fuentes y ~10 % menos tokens por empresa que las rondas anteriores.
2. **Instrucciones cortas y salida mínima:** la pasada rápida escribe 9 columnas, no 17, y corta a las 2 búsquedas.
3. **Reportes de un renglón:** cada agente responde con una línea por empresa; el resumen largo va al CSV, no al chat.
4. **No repetir:** los selectores excluyen lo ya investigado por nombre y por dominio web.
5. **Lotes grandes para lo barato, chicos para lo caro:** 250 nombres por agente de triaje, 30 por pasada rápida, 12 por investigación completa.
6. **Sesiones:** el tope es de 1.500 búsquedas por sesión. Una sesión rinde: 1 tanda completa (96) + 1 rebúsqueda (96) + 1 pasada rápida (240). O bien 3 pasadas rápidas (720).

## Ciclo de una sesión (en este orden)
```bash
./instalar.sh && source .venv/bin/activate
python -m prospeccion todo && python -m prospeccion cartera
# Nivel 2 (una sola vez, hasta agotar los lotes):
PYTHONPATH=. python investigacion/herramientas/armar_triaje.py 250        # lotes en investigacion/triaje/
#   8-10 agentes haiku: «Leé investigacion/herramientas/instrucciones_triaje.md ... Entrada: lote_NN.csv. Salida: lote_NN_out.csv»
PYTHONPATH=. python investigacion/herramientas/sumar_triaje.py            # -> datos/entrada/triaje.csv
python -m prospeccion todo                                               # la cola se reordena con el triaje
# Nivel 3:
PYTHONPATH=. python investigacion/herramientas/elegir_rapida.py q1 240 8
#   8 agentes sonnet con instrucciones_rapida.md (q1_i.csv -> q1_outi.csv)
PYTHONPATH=. python investigacion/herramientas/sumar_rapida.py "q1_out*.csv"
python -m prospeccion todo                                               # el rubro confirmado ya califica
# Nivel 4 y 5: igual que antes (elegir_tanda / sumar, elegir_rebusca / completar)
python -m prospeccion cartera && python -m prospeccion tablero -o <scratchpad>/tablero.html
```

## Qué mirar para decidir si el embudo funciona
- Después del triaje: cuántas quedaron `industrial_objetivo` + `industrial_otro`. Si son más de 4.000, subir el
  umbral (empezar solo por `industrial_objetivo` con dominio propio).
- Después de la primera pasada rápida: qué porcentaje confirmó rubro y cuántas cayeron por descarte. Si menos del
  40 % confirma, el triaje está dejando pasar nombres inútiles: ajustar las instrucciones antes de seguir.
- La sesión local con Chrome (canal/) puede hacer la pasada rápida abriendo las webs, sin gastar búsquedas del tope.
