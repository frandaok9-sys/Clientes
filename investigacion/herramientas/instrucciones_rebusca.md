# Rebúsqueda: completar decisor o canal de empresas ya investigadas (COI, CRM-ERP para PyMEs industriales)

Herramienta: solo WebSearch. WebFetch a webs de empresas está bloqueado por el proxy: no lo uses.
Estas empresas ya fueron investigadas una vez y quedaron sin decisor, sin canal o sin ambos. Tu trabajo es
buscar **solo lo que falta** (columna `falta`), con otras búsquedas distintas a las obvias. Máximo 5 búsquedas por
empresa. No contactes a nadie.

La entrada tiene encabezado: razon_social;localidad;nombre_corto;web;rubro;contacto_nombre;contacto_cargo;contacto_email;contacto_telefono;falta
Lo que ya está cargado es correcto: no lo vuelvas a buscar ni lo cambies.

## Dónde buscar lo que falta
- **Decisor** (dueño / socio gerente / presidente / gerente general / gerente comercial o administrativo):
  web propia (secciones «nosotros», «equipo», «historia»), LinkedIn (cargo actual, buscando `"nombre_corto" gerente`
  o `"razon_social" socio gerente`), prensa local o sectorial (notas, entrevistas, aniversarios), cámaras
  empresariales, Boletín Oficial provincial o nacional (edictos de constitución o designación de autoridades:
  SOLO nombre y cargo, nunca DNI, domicilio ni fecha de nacimiento).
- **Canal** (email o teléfono de la empresa): web propia (página «contacto»), redes de la empresa (Instagram,
  Facebook: el teléfono o WhatsApp comercial que publica la empresa), cámaras y parques industriales (listados
  de socios), guías comerciales. Un email vale solo si aparece **textual** en una fuente pública. Teléfono fijo,
  0810 o WhatsApp comercial publicado por la empresa; nada de celulares personales.

## Reglas duras
- NUNCA inventes ni deduzcas emails por patrón (`info@dominio` sin verlo publicado no vale). Lo que no encuentres queda vacío.
- No uses ZoomInfo, RocketReach, ContactOut, Lusha ni Apollo como fuente de nombres, emails, teléfonos ni empleados.
- Cuidado con homónimos: confirmá localidad o rubro antes de cargar un dato.
- Cada dato nuevo lleva su URL en `fuente`. Sin URL, no cargues el dato.
- Sin ";" dentro de los campos.

## Salida
CSV UTF-8, separador `;`, una fila por empresa de la entrada (aunque no encuentres nada), encabezado exacto:
razon_social;contacto_nombre;contacto_cargo;contacto_email;contacto_telefono;otros_contactos;nota;fuente

- razon_social: exacta como en la entrada.
- Dejá vacío lo que ya venía cargado en la entrada (solo se completan vacíos) y lo que no encontraste.
- contacto_cargo: con la fuente y el año entre paréntesis si se ve (ej. "Socio gerente (BO Santa Fe 2019)").
- otros_contactos: "Nombre (cargo)" separados por " / ".
- nota: qué buscaste y por qué no apareció, o aclaraciones (dato viejo, teléfono de directorio, homónimo).
- fuente: URLs separadas por " | ".

Al terminar, respondé solo con: cuántas filas escribiste y una línea por empresa (qué faltaba, qué encontraste, fuente).
