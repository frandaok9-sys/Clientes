# Pasada rápida de rubro (COI, CRM-ERP para PyMEs industriales argentinas)

Herramienta: solo WebSearch. WebFetch a webs de empresas está bloqueado: no lo uses. **Máximo 2 búsquedas por
empresa** (la primera: `"razon_social" localidad`; la segunda solo si la primera no alcanzó). No contactes a nadie.
Acá NO se busca decisor ni contacto: solo confirmar qué es la empresa. Lo demás se investiga después, solo para las que valgan la pena.

La entrada tiene: razon_social;localidad;provincia;dominio_conocido

## Qué averiguar por empresa (en este orden, y cortá en cuanto lo tengas)
1. ¿Existe y está activa? ¿Tiene web propia? (sin web no es descarte, es dato)
2. ¿Qué hace? Una frase concreta (ej. "fabrica silos y norias para acopio", "distribuye rodamientos y correas").
3. Tamaño si aparece en la web, LinkedIn o prensa (ej. "11-50 (LinkedIn)"). Si no aparece, vacío.
4. Señal de descarte si la hay: multinacional o grupo grande, más de 250 empleados, cerrada, quiebra o
   concurso, consumidor final/minorista, estación de servicio, productor agropecuario, no es empresa.

## Reglas duras
- NUNCA inventes. Si en 2 búsquedas no aparece nada confiable, dejá `rubro` vacío y poné en `alerta` "no encontrada".
- Cuidado con homónimos: si no coincide la localidad (o la provincia), no cargues el dato; anotalo en `alerta`.
- No uses ZoomInfo, RocketReach, ContactOut, Lusha ni Apollo.
- Sin ";" dentro de los campos.

## Salida
CSV UTF-8, separador `;`, una fila por empresa de la entrada (aunque no encuentres nada), encabezado exacto:
razon_social;localidad;provincia;web;rubro;empleados;senales;alerta;fuente

- razon_social y localidad: exactas como en la entrada. provincia: completala si la ves.
- web: dominio propio sin https (vacío si no tiene).
- rubro: qué hace, en pocas palabras. Vacío si no lo confirmaste.
- senales: palabras clave separadas por " | " cuando apliquen: área comercial, vendedores, representantes, obras,
  proyectos, montaje, mantenimiento, minería, energía, petrolera, exportación, nueva planta, expansión.
- alerta: solo si hay señal de descarte o duda de homónimo. Si no, vacío.
- fuente: URLs separadas por " | ". Sin URL no hay dato.

Al terminar, respondé solo con una línea: cuántas filas escribiste, cuántas con rubro confirmado y cuántas con alerta.
