# Traspaso a una sesión local (en tu computadora)

La sesión en la nube no llega a tu escritorio, a Chrome ni al DNS. Esta guía es para seguir el
trabajo en Claude Code instalado en tu computadora.

## Preparar
1. Instalá Claude Code (app de escritorio o `npm install -g @anthropic-ai/claude-code`).
2. Cloná el repo y entrá a la rama:
   ```
   git clone https://github.com/frandaok9-sys/Clientes
   cd Clientes
   git checkout claude/customer-classification-prospecting-uxgdbb
   ```
3. Descomprimí `respaldo_datos.zip` en la carpeta del repo (crea `datos/entrada/...`).
   Tiene datos personales: no lo subas al repo.
4. Instalá dependencias: `./instalar.sh` (en Windows: `python -m venv .venv`, activar el entorno y
   `pip install -r requirements.txt`).
5. Arrancá con Chrome conectado: `claude --chrome`, o desde la app de escritorio.

## Pedido para la sesión local
Pegá esto como primer mensaje:

> Leé CLAUDE.md y contexto/prospeccion-masiva-contexto.md. Corré `python -m prospeccion todo`
> (con DNS local, la verificación de Google Workspace vuelve a funcionar). Después:
> 1. Usá mi carpeta "landing coi" del escritorio para sacar logo, colores, frases y datos de contacto.
>    Completá `plantillas/firma.html` con mis datos reales y el logo (subilo a un lugar público o
>    usá el de la web) y cargala en Zoho Mail (pestaña abierta en Chrome): Configuración → Firmas.
> 2. Revisá el mail de presentación (`plantillas/whatsapp.j2`, que también se usa como cuerpo del
>    email) con el tono de la landing. Tiene que quedar corto, con voseo y orientado a conseguir la
>    reunión. Respetá la sección 9 del brief: ~90 palabras y línea de baja.
> 3. Poné mi nombre como remitente en `config.yaml` (oferta.remitente) y regenerá `mailing.csv`.
> 4. Mandame un mail de prueba a mí mismo desde Zoho con la firma, para ver cómo se ve.
> No envíes nada a prospectos sin que yo lo apruebe.

## Pendientes generales
- 32 fichas de investigación profunda sin hacer y 1.622 empresas en "Próximas a investigar"
  (hoja de `datos/salida/trabajo.xlsx`).
- Verificar los decisores con fuentes viejas antes de contactar.
- Chequear los teléfonos en el Registro «No Llame» antes de llamar.
