# Catálogo · Outlet Línea Blanca San Pedro

Catálogo web informativo OLB, **sin precios ni compra en línea**, orientado a consultar,
visitar la tienda y comprar presencialmente o solicitar despacho a Chile continental.
La disponibilidad para despacho se actualiza desde Tótem. El surtido se complementa
con el archivo interno `vigentes.json`, generado desde la planilla vigente de San
Pedro. Este proceso administrativo no aparece en la interfaz pública.

La grilla no muestra stock. Al abrir un producto se muestran marca, referencia,
dimensiones publicadas y disponibilidad para despacho. Como el stock puede cambiar
durante el día, el sitio pide confirmar siempre llamando al teléfono fijo
**+56 41 290 7387**. WhatsApp se incorporará más adelante.

El catálogo se puede ordenar por nombre o por precio. El precio actualizado se usa
solo para definir el orden y no se presenta al público en esta etapa informativa.

Las garantías no aparecen como productos. El catálogo incluye una explicación breve
de la garantía legal, voluntaria y especial. Productos y accesorios/repuestos se
presentan en pestañas separadas.

## Archivos

- **index.html** — estructura y estilos del catálogo.
- **OLB_LOGO_OFICIAL_2026_SAN_PEDRO_ELECTROLUX_MADEMSA.png** — logo oficial exacto sobre fondo negro.
- **catalogo.js** — filtros, ficha de producto, dimensiones, despacho y llamadas a tienda.
- **datos_catalogo.js** — salida técnica completa del recolector, conservada como base de trabajo.
- **feed/catalogo_publico.json** — datos controlados que carga el catálogo publicado.
- **feed/catalogo_publico.js** — respaldo integrado para abrir `index.html` directamente.
- **vigentes.json** — SKU y descripción vigentes de San Pedro, importados desde la planilla oficial entregada por la tienda.
- **actualizar_vigentes.py** — reemplaza internamente la lista vigente desde un nuevo Excel, sin agregar controles al sitio público.
- **fuentes_oficiales.json** — caché interna de fichas e imágenes verificadas por SKU en Electrolux, Mademsa y Fensa.
- **armar_catalogo_auto.py** — cruza la lista vigente con Tótem y arma `productos.json`, `catalogo_meta.json` y `datos_catalogo.js` (usa el Extractor OLB para las imágenes).
- **publicacion_control.json** — copia de trabajo de las decisiones PUBLICAR/REVISAR/OCULTAR del informe en Drive.
- **generar_feed_publico.py** — crea en `feed/` una salida liviana usando publicaciones automáticas más aprobaciones manuales.
- **verificar_feed_publico.py** — comprueba que el feed no incluya pendientes, ocultos, duplicados ni fichas sin imagen.
- **extractor_olb.py** — Extractor OLB (lo usa el script anterior; también se puede correr solo: `python extractor_olb.py MODELO --descargar`).
- **.github/workflows/actualizar.yml** — corre el proceso una vez al día.

## Publicar / actualizar en tu repositorio

1. Sube todo el contenido de esta carpeta al repositorio oficial, incluida la carpeta `feed/`.
2. **Settings → Actions → General → Workflow permissions → Read and write**.
3. **Actions → Actualizar catálogo → Run workflow** (actualiza la base, genera el feed controlado y lo valida antes de guardar cambios).
4. **Settings → Pages** → rama `main`, carpeta `/ (root)`.

De ahí en adelante se actualiza solo cada día.

La regla de publicación combina dos fuentes: se muestra un SKU si está en el archivo
interno de vigentes o si Tótem registra stock para despacho. El stock de Tótem se usa
solo para informar despacho y no representa por sí solo todo lo disponible en tienda.
Un SKU sin vigencia y sin stock se oculta aunque exista en el maestro. Los accesorios
y repuestos siguen la misma regla.

Para los SKU vigentes sin imagen en Tótem, la actualización cruza por código exacto
los catálogos oficiales de Electrolux, Mademsa y Fensa y conserva la última ficha
verificada. Garantías, visitas, conexiones, instalaciones y otros servicios se
excluyen como artículos. También se ocultan kits, combos, packs y referencias
combinadas; la única excepción son los conjuntos de aire acondicionado.

Para renovar la lista interna se ejecuta `python actualizar_vigentes.py "archivo.xlsx"`
y luego el actualizador normal del catálogo. El importador detecta las columnas SKU y
DESCRIPCION y conserva los datos oficiales adicionales ya verificados por código.

El catálogo carga inicialmente 24 resultados y agrega más a pedido. Solo publica la
primera imagen utilizada por cada ficha, difiere la carga de fotografías y reutiliza
los datos en caché cuando corresponde.

## Feed público controlado

El feed nuevo se genera con `python generar_feed_publico.py` y se valida con
`python verificar_feed_publico.py`. Sus archivos quedan dentro de `feed/` y son la
fuente que utiliza la página. La salida mantiene una sola imagen por ficha, unifica
categorías equivalentes y conserva el precio únicamente para el orden interno.

La regla del feed es: incluir las filas `PUBLICAR` de `CRUCE_SKU` y las filas de
`REVISAR` cuya `Decisión final` sea `Publicar`. Las decisiones `Pendiente` y
`Ocultar` nunca entran. Si una ficha aprobada no está en `productos.json`, se
reconstruye con los datos verificados del informe en vez de descartarla.

## Ajustes

- Datos de la tienda (nombre, teléfono fijo, dirección, mapa): constante `CONFIG` en `catalogo.js`.
- Color de marca: variable `--accent` al inicio de index.html.
- Marcas / tamaño de imagen: al inicio de armar_catalogo_auto.py (`MARCAS`, `IMG_LADO`).
- Términos excluidos como garantías o servicios: `PATRON_NO_CATALOGO` en armar_catalogo_auto.py.
