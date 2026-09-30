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
   exige aprobación para workflows de colaboradores externos. El workflow
   diario declara `contents: read`, no tiene job de escritura y usa acciones
   fijadas a SHA completo.
4. Revisa las ejecuciones de `Preparar actualización diaria del catálogo` y
   publica el artefacto validado desde una cuenta autorizada. La actualización
   automática del sitio requiere un acceso de despliegue limitado a Cloudflare
   Pages, separado del permiso general de escritura a GitHub.
5. En tu cuenta GitHub, activa autenticación en dos pasos o passkey y guarda
   los códigos de recuperación fuera del computador. Revisa sesiones,
   aplicaciones y tokens personales que ya no uses.

## Actualización diaria

El workflow diario genera y valida una propuesta descargable en Actions. No
ejecuta `git push`. El último sitio publicado sigue visible si una consulta
falla; la disponibilidad deja de mostrarse como reciente después de 24 horas.
Una publicación manual en `main` activa Cloudflare Pages si el proyecto
`olbsanpedro` tiene habilitada la integración Git y `main` como producción.

La conexión de Codex con GitHub opera con los permisos que autorices a la
aplicación y bajo tu cuenta conectada; Codex no es un segundo dueño autónomo.
No autorices a una aplicación con permisos amplios que no necesites.
