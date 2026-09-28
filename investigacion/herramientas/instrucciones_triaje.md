# Triaje por nombre (sin buscar en la web)

Vas a recibir un CSV con empresas argentinas: `razon_social;localidad;dominio_email`. Solo con el nombre (y el
dominio del email si lo hay) tenés que decir **qué tan probable es que sea una PyME industrial B2B**, cliente
objetivo de COI (CRM-ERP para metalúrgicas, montajes, instalaciones, mantenimiento industrial, proveedores de
minería/energía/agroindustria, pisos industriales y distribuidoras de insumos industriales).

**No busques nada en internet. No uses herramientas. No inventes datos.** Esto es solo un orden de prioridad para
decidir a quién investigar primero; no es un dato de la empresa y nunca se muestra como rubro.

## Clases (una por fila)
- `industrial_objetivo`: el nombre o el dominio sugiere claramente industria, metalúrgica, ingeniería, montajes,
  instalaciones, servicios industriales, fundición, mecanizado, hidráulica, neumática, maquinaria, insumos industriales,
  construcción industrial, proveedor minero o petrolero, agroindustria (maquinaria, silos, riego, empaque).
- `industrial_otro`: parece empresa B2B pero no está claro que sea industrial: distribuidoras, transportes,
  logística, construcción en general, servicios técnicos genéricos, químicas, plásticos, madereras, alimentos con
  planta, importadoras, "S.A." o "S.R.L." con nombre que no dice el rubro.
- `no_objetivo`: claramente no es cliente: comercio minorista (kiosco, tienda, indumentaria, farmacia,
  gastronomía, supermercado), profesionales y estudios (contables, jurídicos, médicos), inmobiliarias, seguros,
  bancos, escuelas, clubes, iglesias, organismos públicos, cooperativas de servicios, productores agropecuarios
  (estancias, campos, "agropecuaria" sin otra señal industrial), nombres de persona sin marca, sucesiones.
- `indeterminado`: no se puede decir nada con el nombre.

Ante la duda entre `no_objetivo` e `indeterminado`, elegí `indeterminado` (descartar por nombre es peor que
investigar de más). Ante la duda entre `industrial_objetivo` e `industrial_otro`, elegí `industrial_otro`.

## Salida
CSV UTF-8, separador `;`, una fila por cada empresa de la entrada, en el mismo orden, encabezado exacto:
razon_social;localidad;triaje;motivo

- razon_social y localidad: exactas como en la entrada.
- triaje: una de las cuatro clases, en minúsculas.
- motivo: 3 a 8 palabras (ej. "metalúrgica en el nombre", "kiosco", "nombre de persona").
- Sin ";" dentro de los campos.

Escribí el archivo de salida con la herramienta Write y respondé solo con: cuántas filas escribiste y cuántas de cada clase.
