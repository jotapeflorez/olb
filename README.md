# Catálogo OLB · San Pedro

Catálogo informativo del Outlet Línea Blanca San Pedro, Mall Arauco Premium
Outlet, Local 38. No publica precios ni ofrece compra en línea. Cada tarjeta
enlaza a una ficha **dentro de OLB** con fotos, medidas y especificaciones
verificadas para su SKU. La ficha invita a llamar al **+56 41 290 7387**.
El comparador admite hasta tres modelos de una misma categoría.

## Datos y publicación

La fuente de despacho es Tótem ShopClub. Electrolux, Mademsa y Fensa
complementan imágenes y especificaciones mediante su API de catálogo **VTEX**
cuando coinciden las referencias exactas; las URL de sus tiendas se conservan
solo en archivos operativos, nunca como enlaces de “Más información” para
clientes. No se presupone que estos catálogos sean Shopify.

El proceso mantiene la regla existente: solo se publican los SKU de
`publicacion_control.json` aprobados por regla automática o revisión manual.
Pendientes, ocultos, servicios y packs no permitidos quedan fuera. Las fichas
reconstruidas desde un control anterior no se tratan como evidencia de stock.

La disponibilidad pública se consulta desde `feed/stock.json`. Una señal
positiva de Tótem se presenta únicamente cuando su observación tiene menos de
24 horas. Si no hay señal vigente, el visitante ve “Consultar disponibilidad”.
La cantidad ofrecida por la API no es inventario de la sala OLB y no se
presenta al cliente. Siempre se confirma despacho y condiciones en tienda.

## Archivos principales

| Archivo | Función |
| --- | --- |
| `index.html`, `catalogo.js` | Grilla, búsqueda, filtros y selección de comparación |
| `p/<SKU>.html`, `ficha.css`, `ficha.js` | Páginas internas con URL compartible, ficha técnica y galería |
| `comparar.html`, `comparar.js` | Comparación por categoría |
| `armar_catalogo_auto.py` | Consulta Tótem y catálogos oficiales VTEX por SKU |
| `generar_feed_publico.py` | Aplica el control de publicación y crea feed liviano y stock |
| `generar_fichas.py` | Genera HTML y JSON de cada SKU publicado |
| `verificar_feed_publico.py` | Valida decisiones, SKU, datos y enlaces internos |
| `feed/catalogo_olb_os.csv` | Salida operativa con URL de origen, separada de la interfaz |

Los archivos `productos.json`, `vigentes.json`, `fuentes_oficiales.json`,
`publicacion_control.json` y `catalogo_meta.json` alimentan la generación.
Las páginas no incrustan HTML, iframe ni manuales externos de proveedores.
Cuando faltan características se indica expresamente. No se deduce una
garantía especial para un modelo sin dato en su ficha.

## Actualizar

```bash
python armar_catalogo_auto.py
python generar_feed_publico.py
python generar_fichas.py
python generar_feed_olb_os.py
python verificar_feed_publico.py
```

El workflow `.github/workflows/actualizar.yml` ejecuta la secuencia a
diario y guarda los resultados solo si pasa la validación. Para probar el
sitio localmente:

```bash
python -m http.server 8000
```

Abrir `http://localhost:8000/`. GitHub Pages puede publicar la rama
`main` desde la carpeta raíz. Si una ficha aprobada deja de publicarse, el
generador retira sus HTML y JSON antiguos.

### Límites de la información

El feed antiguo tenía una foto por SKU y muchos productos sin modelo o
especificaciones. El recolector actualizado puede traer hasta ocho fotos y
sus atributos técnicos por SKU en la próxima actualización. El lote incluido
en esta entrega incorpora fichas enriquecidas de M100DI, M150DI, M200DI y
M400DI como ejemplos reales. El resto se enriquece progresivamente cuando
las APIs entregan datos; sus campos faltantes siguen visibles como tales.
