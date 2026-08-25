/* ===================================================================
   sync.js — actualiza productos.json desde shopclub (VTEX)
   -------------------------------------------------------------------
   Recorre TODO el catálogo de la tienda, se queda con las marcas que
   te interesan, y por cada producto extrae: nombre, marca, categoría,
   disponibilidad y los LINKS DE IMÁGENES (ya al tamaño correcto).
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

/* ---- baja el árbol de categorías y devuelve solo las hojas ---- */
async function categoriasHoja() {
  const arbol = await getJSON(`${TIENDA}/api/catalog_system/pub/category/tree/50`) || [];
  const hojas = [];
  const recorrer = nodos => {
    for (const n of nodos) {
      if (n.hasChildren && n.children?.length) recorrer(n.children);
      else hojas.push({ id: n.id, name: n.name });
    }
  };
  recorrer(arbol);
  return hojas;
}

/* ---- transforma la URL de imagen VTEX al tamaño deseado ---- */
function redimensiona(url) {
  return url.replace(/\/arquivos\/ids\/(\d+)(?:-\d+-\d+)?\//, `/arquivos/ids/$1-${IMG}/`);
}

/* ---- convierte un producto de VTEX al formato del catálogo ---- */
function aFormatoCatalogo(p) {
  const item = (p.items && p.items[0]) || {};
  const imagenes = (item.images || [])
    .slice(0, MAX_IMAGENES)
    .map(img => redimensiona(img.imageUrl));

  const disponible = (item.sellers || []).some(
    s => s.commertialOffer && s.commertialOffer.AvailableQuantity > 0
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
    disponible,
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
  console.log("Leyendo categorías…");
  const hojas = await categoriasHoja();
  console.log(`  ${hojas.length} categorías encontradas`);

  const porId = new Map();  // dedup por productId (un producto vive en varias categorías)

  for (const cat of hojas) {
    const productos = await productosDeCategoria(cat.id);
    for (const p of productos) {
      if (marcasOK.length && !marcasOK.includes((p.brand || "").toLowerCase())) continue;
      if (!porId.has(p.productId)) porId.set(p.productId, aFormatoCatalogo(p));
    }
    console.log(`  ${cat.name}: ${productos.length} productos (acumulado ${porId.size})`);
    await dormir(PAUSA_MS);
  }

  const salida = [...porId.values()]
    .filter(p => p.imagenes.length)                 // descarta los que no traen imagen
    .sort((a, b) => a.nombre.localeCompare(b.nombre));

  const fs = await import("node:fs/promises");
  await fs.writeFile("productos.json", JSON.stringify(salida, null, 2), "utf8");
  console.log(`\n✓ Listo: ${salida.length} productos escritos en productos.json`);
}

main().catch(e => { console.error("Error:", e); process.exit(1); });
