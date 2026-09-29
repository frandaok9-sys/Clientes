# Prospección de empresas industriales argentinas para COI (CRM-ERP para PyMEs industriales)

Herramienta: solo WebSearch. WebFetch a webs de empresas está bloqueado por el proxy: no lo uses.
Máximo 5 búsquedas por empresa (si en 2 búsquedas ya ves que es grande, multinacional o no existe, cortá y cargá la alerta). No contactes a nadie.

> **Sesión local (desde el 29-09):** también podés usar WebFetch para abrir la web propia cuando el buscador no alcance (cuenta como una de las búsquedas). Ritmo para no quedar bloqueados por scraping: de a una página, como máximo 3 por sitio, sin ráfagas; si un sitio da error, límite o captcha, no insistas. **No abras LinkedIn con WebFetch**: si solo LinkedIn tendría el dato, anotalo en `nota` y lo mira la sesión principal con pausas.

La entrada tiene: razon_social;localidad;provincia;dominio_conocido;rubro_supuesto

## Qué averiguar por empresa
1. Si existe y está activa, web propia (o si NO tiene web: eso es dato, no descarte), qué hace, tamaño.
2. Decisor: dueño / socio gerente / presidente / gerente general / gerente comercial o administrativo.
   Fuentes válidas: web propia, LinkedIn (cargo actual), prensa local o sectorial, cámaras, Boletín Oficial
   (edictos: SOLO nombre y cargo, nunca DNI, domicilio ni fecha de nacimiento).
3. Canal publicado: email de la empresa o del área comercial (ventas@, info@...) o de la persona SOLO si
   aparece textual en una fuente pública; teléfono fijo de la empresa, 0810 o WhatsApp comercial que la
   empresa publica. Nada de celulares personales.
4. Un gancho concreto y verificable para abrir un mensaje (obra, exportación, lanzamiento, aniversario,
   certificación, búsqueda laboral), con año si se ve.
5. Señales de descarte: multinacional o parte de grupo grande, más de 250 empleados, cerrada, quiebra o
   concurso, consumidor final/minorista, estación de servicio, cooperativa de servicios públicos, no es empresa.

## Reglas duras
- NUNCA inventes ni deduzcas emails por patrón. Lo que no encuentres textual queda vacío.
- No uses ZoomInfo, RocketReach, ContactOut, Lusha ni Apollo como fuente de nombres, emails, teléfonos ni empleados.
- Cuidado con homónimos: confirmá la localidad.
- Sin ";" dentro de los campos.

## Salida
CSV UTF-8, separador `;`, una fila por empresa de la entrada (aunque no encuentres nada), encabezado exacto:
razon_social;localidad;provincia;nombre_corto;web;rubro;empleados;senales;contacto_nombre;contacto_cargo;contacto_email;contacto_telefono;otros_contactos;dato;alerta;nota;fuente_enriquecimiento

- razon_social, localidad: exactas como en la entrada. provincia: completala si la sabés.
- nombre_corto: como la conoce la gente (marca o nombre sin S.R.L.).
- web: dominio propio sin https (vacío si no tiene web propia).
- rubro: qué hace, en pocas palabras.
- empleados: solo si la web, LinkedIn o prensa lo dicen, con la fuente entre paréntesis (ej. "11-50 (LinkedIn)").
- senales: frases con " | " usando estas palabras cuando apliquen: área comercial, vendedores, representantes,
  obras, proyectos, montaje, mantenimiento, minería, energía, petrolera, renovables, exportación,
  búsqueda laboral, nueva planta, expansión.
- contacto_cargo: incluí la fuente y el año entre paréntesis si se ve (ej. "Socio gerente (BO Santa Fe 2018)").
- otros_contactos: "Nombre (cargo)" separados por " / ".
- dato: una frase que EMPIECE con el nombre_corto y siga en presente o pasado, sin punto final
  (ej. "Gan Mar exporta polipastos a ocho países de América Latina"). No uses datos sensibles (accidentes, juicios, concursos).
- alerta: solo si hay señal de descarte o algo que conviene revisar antes de contactar. Si no, vacío.
- nota: aclaraciones útiles (dato viejo, homónimo, teléfono de directorio, sin web propia).
- fuente_enriquecimiento: URLs separadas por " | ".

Al terminar, respondé solo con: cuántas filas escribiste y una línea por empresa (encontrada/no, decisor sí/no, canal sí/no, alerta).
