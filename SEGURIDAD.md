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
2. En `Settings → Rules → Rulesets`, crea un **New branch ruleset** llamado
   `Publicación controlada OLB`, con estado **Active** y objetivo `main`.
   Activa **Restrict updates**, **Restrict deletions**, **Block force pushes**
   y **Require a pull request before merging**. Configura **0 approvals**:
   el dueño de una cuenta personal no puede aprobar su propio pull request.
   En la lista de excepciones, permite a **Repository admins** únicamente
   **For pull requests only**. Primero comprueba que solo tú tienes ese rol.
   Si se configura una restricción sin esa excepción, podrías impedirte
   publicar hasta corregir la regla desde Settings.
3. Tras el primer pull request que ejecute `Verificar cambios OLB / verificar`,
   añade ese status check como obligatorio en el mismo ruleset. No selecciones
   un nombre de check que aún no haya aparecido, para evitar bloquear la rama.
4. En `Settings → Actions → General`, deja **Workflow permissions** en solo
   lectura, desactiva que Actions pueda crear o aprobar pull requests, exige
   aprobación para ejecutar workflows de colaboradores externos y, si aparece
   la opción, exige acciones fijadas a SHA completo. Los workflows del
   repositorio ya declaran `contents: read`, no guardan credenciales de Git
   y usan versiones de acciones fijadas a un SHA.
5. En tu cuenta GitHub, activa autenticación en dos pasos o passkey y guarda
   los códigos de recuperación fuera del computador. Revisa sesiones,
   aplicaciones y tokens personales que ya no uses.

## Actualización diaria

El workflow diario genera y valida una propuesta descargable en Actions.
No ejecuta `git push` y su token no puede escribir contenido. Para publicar,
revisa diferencias, crea una rama o pull request y fusiona la propuesta tú
mismo. Si nadie publica una propuesta, el catálogo sigue visible, pero el
stock deja de presentarse como dato reciente a las 24 horas.

La conexión de Codex con GitHub opera con los permisos que autorices a la
aplicación y bajo tu cuenta conectada; Codex no es un segundo dueño autónomo.
No autorices a una aplicación con permisos amplios que no necesites.
