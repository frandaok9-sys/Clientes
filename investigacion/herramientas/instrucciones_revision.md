# Revisión de alertas: decidir si una empresa se mantiene o se descarta (COI, CRM-ERP para PyMEs industriales)

Estas empresas ya fueron investigadas y quedaron con una **alerta** (columna `alerta`): posible grupo grande,
homónimo, empresa inactiva, decisor viejo, rubro dudoso. Tu trabajo es resolver **esa duda puntual** abriendo
las fuentes, no volver a investigar todo. No contactes a nadie, no llenes formularios, no inicies sesión.

Herramientas: WebFetch (abrí la web propia y sus páginas «Nosotros», «Contacto», «Equipo») y WebSearch (prensa,
Boletín Oficial, cámaras, LinkedIn público). Máximo 6 búsquedas o visitas por empresa.

La entrada es un CSV con encabezado, separador `;`:
razon_social;localidad;web;rubro;categoria;contacto_nombre;contacto_cargo;contacto_email;contacto_telefono;empleados_aprox;alerta;nota;fuente_enriquecimiento

## Ritmo (para no quedar bloqueados por scraping)
- De a una empresa y de a una página: nunca varias visitas en paralelo al mismo sitio.
- A lo sumo 3 páginas por sitio de empresa. Si un sitio responde error, límite o captcha, no insistas: pasá a
  otra fuente y anotalo en `nota`.
- **No abras LinkedIn con WebFetch** (pide login y marca la IP). Si hace falta LinkedIn, anotá en `nota` qué
  habría que mirar ahí; lo hace la sesión principal con pausas.
- Preferí primero WebSearch (no toca los sitios) y abrí con WebFetch solo la página que confirma el dato.

## Criterios (brief de COI, secciones 3 y 4)
- **Mantener:** PyME argentina B2B que vende productos industriales, proyectos o servicios técnicos, de unos 10 a
  250 empleados. Distribuidoras de insumos industriales, instaladores y contratistas también entran.
- **Descartar** (con motivo corto):
  - más de ~250 empleados, o parte de un grupo grande que decide centralmente;
  - filial de multinacional;
  - UTE o consorcio por proyecto;
  - cerrada, en quiebra o sin actividad;
  - comercio minorista o de mostrador para consumidor final;
  - estación de servicio;
  - rubro que no es industrial ni B2B;
  - fuera de Argentina.
- **Dudoso:** si después de buscar no alcanza para decidir, decilo con qué falta. No adivines.

## Reglas duras
- Nunca inventes ni deduzcas datos: sin URL, vacío. Un email vale solo si aparece textual en una fuente pública.
- No uses ZoomInfo, RocketReach, ContactOut, Lusha, Apollo ni Dunsguide como fuente de nombres, emails o empleados.
- Del Boletín Oficial, solo nombre y cargo (nunca DNI, domicilio ni fecha de nacimiento).
- Cuidado con homónimos: confirmá localidad, CUIT o rubro antes de atribuir un dato.
- Sin «;» dentro de los campos.

## Salida
CSV UTF-8, separador `;`, una fila por empresa de la entrada, encabezado exacto:
razon_social;decision;motivo;empleados;contacto_nombre;contacto_cargo;contacto_email;contacto_telefono;nota;fuente

- `razon_social`: exacta como en la entrada.
- `decision`: `mantener`, `descartar` o `dudoso`.
- `motivo`: una frase con el dato que decide (ej. «501-1000 empleados en LinkedIn», «es la misma Chiaza SRL de
  San Lorenzo: web y CUIT coinciden»).
- `empleados`, `contacto_*`: solo si encontraste un dato **nuevo o corregido** con URL; si no, vacío.
- `nota`: lo que conviene saber para contactarla (qué no mencionar, dato viejo, etc.).
- `fuente`: URLs separadas por « | ».

Al terminar respondé solo: cuántas filas escribiste y una línea por empresa con la decisión y el motivo.
