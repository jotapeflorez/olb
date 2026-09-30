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
positiva se presenta únicamente cuando su observación tiene menos de
24 horas: “Hay disponibilidad para despacho” y “Consulta en tienda si hay
stock para entrega inmediata”. Si no hay señal vigente, se invita a consultar
la disponibilidad para despacho. El nombre de la fuente no aparece en la ficha.
La cantidad ofrecida por la API no es inventario de la sala OLB y no se
presenta al cliente. Siempre se confirma despacho y condiciones en tienda.

## Archivos principales

| Archivo | Función |
| --- | --- |
| `index.html`, `catalogo.js` | Grilla, búsqueda, filtros y selección de comparación |
| `p/<SKU>.html`, `ficha.css`, `ficha.js` | Páginas internas con URL compartible, ficha técnica y galería |
| `comparar.html`, `comparar.js` | Comparación por categoría |
| `armar_catalogo_auto.py` | Consulta Tótem y catálogos oficiales VTEX por SKU |
| `enriquecer_fichas.py` | Recupera descripción, datos y fotos de los SKU ya publicados sin alterar stock |
| `enriquecer_oficiales.py` | Busca únicamente las fichas incompletas por SKU exacto en las APIs oficiales |
| `generar_feed_publico.py` | Aplica el control de publicación y crea feed liviano y stock |
| `generar_fichas.py` | Genera HTML y JSON de cada SKU publicado |
| `verificar_feed_publico.py` | Valida decisiones, SKU, datos, enlaces internos y cobertura mínima |
| `feed/calidad_fichas.json` | Conteo real de descripciones, atributos, medidas y galerías visibles |
| `feed/catalogo_olb_os.csv` | Salida operativa con URL de origen, separada de la interfaz |

Los archivos `productos.json`, `vigentes.json`, `fuentes_oficiales.json`,
`publicacion_control.json` y `catalogo_meta.json` alimentan la generación.
Las páginas no incrustan HTML, iframe ni manuales externos de proveedores.
Los apartados de descripción, medidas y características técnicas solo aparecen
cuando contienen datos verificables. Las fotos adicionales se insertan en el
HTML de cada página, sin depender de una segunda descarga de JSON. No se
presenta una oferta genérica de instalación o una garantía especial sin dato
para el producto.

## Actualizar

```bash
python armar_catalogo_auto.py
python generar_feed_publico.py
python generar_fichas.py
python generar_feed_olb_os.py
python verificar_feed_publico.py
```

Para enriquecer una versión ya generada sin cambiar sus decisiones de
publicación ni renovar artificialmente la fecha de stock:

```bash
python enriquecer_fichas.py
python generar_feed_publico.py
python enriquecer_oficiales.py
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

La primera entrega tenía información ampliada en solo cuatro de 500 fichas.
En esta revisión, las 500 fichas publicadas incluyen 487 con descripción, 362
con atributos técnicos visibles, 383 con medidas y 466 con varias fotos.
Las 13 restantes sin texto ni atributos pertenecen principalmente a repuestos
o registros antiguos sin ficha verificable: se muestran nombre, código, foto
y una forma de consultar en tienda, sin inventar especificaciones. La
auditoría falla si las fuentes dejan caer la cobertura a menos de 60 % en
descripciones o 50 % en atributos técnicos y galerías.
