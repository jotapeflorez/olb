/* ===================================================================
   sync.js — actualiza productos.json desde shopclub (VTEX)
   -------------------------------------------------------------------
   Recorre TODO el catálogo de la tienda, se queda con las marcas que
   te interesan, y por cada producto extrae: nombre, marca, categoría,
   dimensiones, disponibilidad para despacho y los LINKS DE IMÁGENES.
   Escribe todo en productos.json, que es el archivo que lee tu
   catálogo (index.html).

   Uso local (necesitas Node 18+):
       node sync.js
   En automático lo corre GitHub Actions una vez al día (ver README).
=================================================================== */

const TIENDA = "https://www.totem.shopclub.cl";

// Marcas que quieres mostrar. Deja el arreglo vacío []  para traer TODAS.
const MARCAS = ["Electrolux", "Fensa", "Mademsa"];

const IMG = "800-800";     // tamaño de las imágenes (ancho-alto en px)
const MAX_IMAGENES = 4;    // cuántas imágenes guardar por producto
const PAGINA = 50;         // productos por consulta (máximo de VTEX)
const PAUSA_MS = 250;      // pausa entre consultas, para no saturar

const dormir = ms => new Promise(r => setTimeout(r, ms));
const marcasOK = MARCAS.map(m => m.toLowerCase());
const RE_NO_CATALOGO = /garant|extendid|servicio t|instalaci|conexi[oó]n|visita|p[oó]liza|cobertura|plan de protecc/i;

/* ---- fetch con reintentos ---- */
async function getJSON(url, reintentos = 3) {
  for (let i = 0; i < reintentos; i++) {
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (res.ok) return await res.json();
      if (res.status === 404) return null;
    } catch (_) { /* reintenta */ }
    await dormir(600 * (i + 1));
  }
  return null;
}

/* ---- baja el árbol y devuelve todas las categorías, incluidos sus padres ---- */
async function categoriasTienda() {
  const arbol = await getJSON(`${TIENDA}/api/catalog_system/pub/category/tree/50`) || [];
  const categorias = [];
  const recorrer = nodos => {
    for (const n of nodos) {
      categorias.push({ id: n.id, name: n.name });
      recorrer(n.children || []);
    }
  };
  recorrer(arbol);
  if (!categorias.length) throw new Error("Tótem no devolvió categorías; se conserva el último catálogo válido.");
  return [...new Map(categorias.map(c => [c.id, c])).values()];
}

/* ---- transforma la URL de imagen VTEX al tamaño deseado ---- */
function redimensiona(url) {
  return url.replace(/\/arquivos\/ids\/(\d+)(?:-\d+-\d+)?\//, `/arquivos/ids/$1-${IMG}/`);
}

function valorEspecificacion(p, ...nombres) {
  for (const nombre of nombres) {
    let valor = p[nombre];
    if (Array.isArray(valor)) valor = valor.find(v => String(v).trim());
    if (valor != null && String(valor).trim()) return String(valor).trim();
  }
  return "";
}

function dimensionesDe(p) {
  const dimensiones = {
    alto: valorEspecificacion(p, "Altura (Centímetros)", "Alto producto", "Altura producto", "Alto"),
    ancho: valorEspecificacion(p, "Ancho (Centímetros)", "Ancho producto", "Ancho"),
    profundidad: valorEspecificacion(p, "Profundidad (Centímetros)", "Profundidad producto", "Profundidad"),
  };
  return Object.fromEntries(Object.entries(dimensiones).filter(([, valor]) => valor));
}

function esServicioOculto(p) {
  return RE_NO_CATALOGO.test(`${p.productName || ""} ${(p.categories || []).join(" ")}`);
}

function tipoCatalogoDe(p) {
  const categorias = (p.categories || []).join(" ").toLowerCase();
  return categorias.includes("/accesorios/") || categorias.includes("/repuestos/")
    ? "accesorios"
    : "productos";
}

/* ---- convierte un producto de VTEX al formato del catálogo ---- */
function aFormatoCatalogo(p) {
  const item = (p.items && p.items[0]) || {};
  const imagenes = (item.images || [])
    .slice(0, MAX_IMAGENES)
    .map(img => redimensiona(img.imageUrl));

  const despachoDisponible = (p.items || []).some(itemVtex =>
    (itemVtex.sellers || []).some(s => s.commertialOffer && s.commertialOffer.AvailableQuantity > 0)
  );
  const precios = (p.items || []).flatMap(itemVtex =>
    (itemVtex.sellers || [])
      .map(seller => Number(seller.commertialOffer && seller.commertialOffer.Price))
      .filter(precio => Number.isFinite(precio) && precio > 0)
  );

  const ruta = (p.categories && p.categories[0]) || "";
  const categoria = ruta.split("/").filter(Boolean).pop() || "Electrohogar";

  const ref = (item.referenceId && item.referenceId[0]?.Value) || p.productReference || "";

  return {
    id: String(p.productId),
    ref: String(ref),
    nombre: p.productName,
    marca: p.brand,
    categoria,
    tipo_catalogo: tipoCatalogoDe(p),
    despacho_disponible: despachoDisponible,
    precio: precios.length ? Math.min(...precios) : null,
    dimensiones: dimensionesDe(p),
    imagenes,
  };
}

/* ---- pagina todos los productos de una categoría ---- */
async function productosDeCategoria(catId) {
  const out = [];
  let from = 0;
  while (from < 2500) {                       // ventana máxima de la API pública
    const to = from + PAGINA - 1;
    const url = `${TIENDA}/api/catalog_system/pub/products/search?fq=C:${catId}&_from=${from}&_to=${to}`;
    const lote = await getJSON(url);
    if (!Array.isArray(lote) || lote.length === 0) break;
    out.push(...lote);
    if (lote.length < PAGINA) break;
    from += PAGINA;
    await dormir(PAUSA_MS);
  }
  return out;
}

async function main() {
  const fs = await import("node:fs/promises");
  console.log("Leyendo categorías…");
  const categorias = await categoriasTienda();
  console.log(`  ${categorias.length} categorías encontradas`);

  const porId = new Map();  // dedup por productId (un producto vive en varias categorías)
  const serviciosOmitidos = new Set();

  for (const cat of categorias) {
    const productos = await productosDeCategoria(cat.id);
    for (const p of productos) {
      if (marcasOK.length && !marcasOK.includes((p.brand || "").toLowerCase())) continue;
      if (esServicioOculto(p)) {
        serviciosOmitidos.add(String(p.productId || p.productReference || p.productName));
        continue;
      }
      if (!porId.has(p.productId)) porId.set(p.productId, aFormatoCatalogo(p));
    }
    console.log(`  ${cat.name}: ${productos.length} productos (acumulado ${porId.size})`);
    await dormir(PAUSA_MS);
  }

  const salida = [...porId.values()]
    .filter(p => p.imagenes.length)                 // descarta los que no traen imagen
    .sort((a, b) => a.tipo_catalogo.localeCompare(b.tipo_catalogo) || a.categoria.localeCompare(b.categoria) || a.nombre.localeCompare(b.nombre));

  if (!salida.length) throw new Error("Tótem no devolvió productos válidos; se conserva el último catálogo válido.");

  await fs.writeFile("productos.json", JSON.stringify(salida, null, 2), "utf8");
  const meta = {
    actualizado_utc: new Date().toISOString(),
    fuente_disponibilidad: TIENDA,
    productos: salida.length,
    disponibles_despacho: salida.filter(p => p.despacho_disponible).length,
    cantidad_productos: salida.filter(p => p.tipo_catalogo === "productos").length,
    cantidad_accesorios_repuestos: salida.filter(p => p.tipo_catalogo === "accesorios").length,
  };
  await fs.writeFile("catalogo_meta.json", JSON.stringify(meta, null, 2), "utf8");
  await fs.writeFile(
    "datos_catalogo.js",
    `window.OLB_PRODUCTOS = ${JSON.stringify(salida)};\nwindow.OLB_CATALOGO_META = ${JSON.stringify(meta)};\n`,
    "utf8"
  );
  console.log(`\n✓ Listo: ${salida.length} productos escritos en productos.json`);
  console.log(`✓ Disponibilidad para despacho: ${meta.disponibles_despacho}`);
  console.log(`✓ Productos: ${meta.cantidad_productos}`);
  console.log(`✓ Accesorios y repuestos: ${meta.cantidad_accesorios_repuestos}`);
  console.log(`✓ Garantías/servicios omitidos del catálogo: ${serviciosOmitidos.size}`);
}

main().catch(e => { console.error("Error:", e); process.exit(1); });
