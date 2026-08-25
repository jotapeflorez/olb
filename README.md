# Catálogo · Electrolux San Pedro

Catálogo web con la marca de la tienda, **sin precios**, con llamado a la acción
para ir al local, pestaña **Garantías** aparte, y **actualización diaria automática**.

## Archivos

- **index.html** — el catálogo (logo, filtros, pestañas Catálogo/Garantías). Autocontenido: el logo va dentro.
- **armar_catalogo_auto.py** — descubre todo el catálogo de la tienda y arma productos.json + garantias.json (usa el Extractor OLB para las imágenes). No requiere lista manual.
- **extractor_olb.py** — Extractor OLB (lo usa el script anterior; también se puede correr solo: `python extractor_olb.py MODELO --descargar`).
- **.github/workflows/sync.yml** — corre el proceso una vez al día, solo.

## Publicar / actualizar en tu repositorio

1. Sube al raíz: `index.html`, `armar_catalogo_auto.py`, `extractor_olb.py` (y la carpeta `.github`).
2. **Settings → Actions → General → Workflow permissions → Read and write**.
3. **Actions → Actualizar catálogo → Run workflow** (genera productos.json y garantias.json).
4. **Settings → Pages** → rama `main`, carpeta `/ (root)`.

De ahí en adelante se actualiza solo cada día.

## Ajustes

- Datos de la tienda (nombre, WhatsApp +56 9 8923 6138, dirección, mapa): constante `CONFIG` al final de index.html.
- Color de marca: variable `--accent` al inicio de index.html.
- Marcas / tamaño de imagen: al inicio de armar_catalogo_auto.py (`MARCAS`, `IMG_LADO`).
- Términos que se apartan a Garantías: `PATRON_GARANTIA` en armar_catalogo_auto.py.
