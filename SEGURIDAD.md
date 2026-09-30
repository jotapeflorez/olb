# Control de cambios del catálogo OLB

El catálogo es público para consulta. Publicar cambios requiere acceso de
escritura al repositorio GitHub. Un visitante puede proponer un pull request o
crear una copia, pero eso no altera el repositorio OLB.

## Protecciones que requiere el dueño en GitHub

1. En `Settings → Collaborators`, revisa quién tiene acceso de escritura y
   elimina a quien no deba publicar. Revisa también `Settings → Deploy keys`:
   no debe haber claves ajenas con permiso de escritura. En la configuración
   de tu cuenta, revisa las aplicaciones GitHub/OAuth autorizadas y limita las
   que no uses.
2. En `Settings → Rules → Rulesets`, crea un ruleset activo para `main` que
   bloquee eliminaciones y `force push` y exija un pull request. Como único
   administrador puedes usar **0 aprobaciones**; confirma que solo tu cuenta
   tenga ese rol antes de permitir una excepción para administradores.
   Comprueba la regla con un cambio pequeño antes de exigir status checks.
3. En `Settings → Actions → General`, deja el permiso predeterminado en
   solo lectura, desactiva que Actions pueda crear o aprobar pull requests y
   exige aprobación para workflows de colaboradores externos. Ambos jobs
   diarios declaran `contents: read`; no hacen commit ni `git push`. Las
   acciones externas se fijan a SHA completo.
4. Para la publicación diaria del sitio, crea un token de Cloudflare limitado
   a la cuenta OLB con permiso **Account → Cloudflare Pages → Edit**. Guárdalo
   en GitHub Actions como `CLOUDFLARE_API_TOKEN`, junto al ID de cuenta en
   `CLOUDFLARE_ACCOUNT_ID`. Habilita la variable de Actions
   `OLB_PUBLICACION_DIARIA=SI` después de revisar esos permisos. No copies el
   token al repositorio ni lo envíes por
   chat. El token permite desplegar proyectos Pages de esa cuenta; revócalo
   si pierde vigencia o se sospecha exposición. El workflow no tiene acceso
   automático a otros permisos de GitHub.
5. En tu cuenta GitHub, activa autenticación en dos pasos o passkey y guarda
   los códigos de recuperación fuera del computador. Revisa sesiones,
   aplicaciones y tokens personales que ya no uses.

## Actualización diaria

El workflow diario genera y valida un artefacto descargable en Actions. Con
las dos credenciales configuradas, publica solo páginas y feeds desde `dist/`
en el proyecto Pages `olbsanpedro`, sin cambiar la rama `main`. Comprueba la
fecha de stock servida después del despliegue. El mismo job desactiva en ese
proyecto los despliegues Git automáticos de producción y de vistas previas:
si permanecen activos, un commit a `main` puede volver a publicar la raíz del
repositorio, incluidos archivos que no pertenecen al sitio. Antes de cambiar
esa configuración, el job comprueba que el proyecto está conectado a
`jotapeflorez/olb` y a la rama `main`.

Sin credenciales, no despliega;
el último sitio sigue visible y el stock deja de mostrarse como reciente a
las 24 horas. La publicación de cambios de código continúa bajo el control
de la rama GitHub.

La conexión de Codex con GitHub opera con los permisos que autorices a la
aplicación y bajo tu cuenta conectada; Codex no es un segundo dueño autónomo.
No autorices a una aplicación con permisos amplios que no necesites.
