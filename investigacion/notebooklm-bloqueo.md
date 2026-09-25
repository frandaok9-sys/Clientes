# Bloqueo: investigación NotebookLM (2026-09-25)

La sesión local no pudo hacer la consulta a NotebookLM.

- Claude in Chrome está conectado (Chrome en Windows).
- El filtro del modo automático de Claude Code bloqueó la navegación a
  `notebooklm.google.com` (motivo: "Browser Navigate Exfil"), porque el pedido
  llegó desde otra sesión y no directamente del usuario.
- También bloqueó el chequeo automático del repo cada 30 segundos (motivo: "Create Unsafe Agents").

Para seguir, el usuario tiene que cambiar los permisos de la sesión local (una
regla de permiso o el modo de permisos). Otra opción es pedírselo directamente
en el chat local.
