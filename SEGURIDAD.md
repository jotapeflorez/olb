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
2. En `Settings → Rules → Rulesets`, protege `main` contra eliminaciones y
   `force push`. **No actives `Require a pull request` ni `Restrict updates`
   para `main` sin haber definido un publicador autorizado que pueda sortear
   la regla**: el commit diario usa `GITHUB_TOKEN` y quedaría bloqueado.
   Si deseas exigir PR para absolutamente todo cambio de código, conviene
   migrar la publicación diaria a un despliegue directo de Cloudflare Pages
   mediante credenciales limitadas y mantener `main` de solo lectura para
   Actions. No prometemos que el token automático esté limitado por rutas:
   GitHub otorga `contents: write` a todo el repositorio durante ese job.
3. En `Settings → Actions → General`, deja el permiso predeterminado en
   solo lectura, desactiva que Actions pueda crear o aprobar pull requests y
   exige aprobación para workflows de colaboradores externos. El job
   `preparar` declara `contents: read`; únicamente `publicar` declara
   `contents: write`. Las acciones externas se fijan a SHA completo.
4. Revisa los commits atribuidos a `github-actions[bot]` y las ejecuciones
   de `Actualizar catálogo y sitio público`. Si ocurre un cambio fuera de
   `productos.json`, `fuentes_oficiales.json`, `catalogo_meta.json`,
   `datos_catalogo.js`, `feed/` y `p/`, investiga y desactiva el workflow.
5. En tu cuenta GitHub, activa autenticación en dos pasos o passkey y guarda
   los códigos de recuperación fuera del computador. Revisa sesiones,
   aplicaciones y tokens personales que ya no uses.

## Actualización diaria

El workflow diario genera y valida el catálogo sin permiso de escritura. Un
segundo job recupera el artefacto validado, instala solo archivos generados y
los confirma en `main`; la integración Git de Cloudflare Pages despliega ese
commit al sitio público. La automatización es una excepción explícita a la
regla de edición manual exclusiva. Si falla una consulta, validación, push o
despliegue, el último sitio sigue visible y el stock deja de presentarse como
reciente a las 24 horas. Comprueba que en Cloudflare Pages el proyecto
`olbsanpedro` tenga `main` como rama de producción y despliegues automáticos
habilitados.

La conexión de Codex con GitHub opera con los permisos que autorices a la
aplicación y bajo tu cuenta conectada; Codex no es un segundo dueño autónomo.
No autorices a una aplicación con permisos amplios que no necesites.
