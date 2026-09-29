const CONFIG = {
  telefono: "+56412907387",
  telefonoTexto: "+56 41 290 7387",
  direccion: "Mall Arauco Premium Outlet, Local 38 · San Pedro de la Paz",
  maps: "https://www.google.com/maps/place/Outlet+Electrolux+Fensa+Mademsa/@-36.8667758,-73.1402856,663m/data=!3m2!1e3!4b1!4m6!3m5!1s0x9669c99e7bdefd17:0x5a189b5cb4a60b50!8m2!3d-36.8667801!4d-73.1377107!16s%2Fg%2F11v191nznj?entry=ttu",
};
const ICON = '<svg class="ph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M5 10h14M9 6v2M9 14v3"/></svg>';
const CANTIDAD_INICIAL = 24, STORAGE = "olb_comparar_v1";
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const tipoDe = p => p.tipo_catalogo === "accesorios" ? "accesorios" : "productos";
const unico = arr => [...new Set(arr.filter(Boolean))];
let PRODUCTOS = [], vista = "productos", categoria = "Todas", marca = "Todas", termino = "", orden = "nombre", limite = CANTIDAD_INICIAL;
function imgFail(el) { const contenedor = el.parentNode; el.remove(); contenedor.insertAdjacentHTML("beforeend", ICON); }
function seleccion() { try { return JSON.parse(sessionStorage.getItem(STORAGE) || "[]"); } catch { return []; } }
function guardar(lista) { sessionStorage.setItem(STORAGE, JSON.stringify(lista)); pintarComparacion(); renderGrid(); }
function pintarComparacion() {
  const lista = seleccion();
  document.getElementById("compareBar").hidden = !lista.length;
  document.getElementById("compareCount").textContent = `${lista.length} de 3 modelos`;
  document.getElementById("compareLink").href = `comparar.html?ref=${lista.map(x => encodeURIComponent(x.ref)).join(",")}`;
}
function alternarComparacion(p) {
  const lista = seleccion();
  if (lista.some(x => x.ref === p.ref)) { guardar(lista.filter(x => x.ref !== p.ref)); return; }
  if (lista.length && (lista[0].categoria !== p.categoria || lista[0].tipo !== tipoDe(p))) {
    alert("Para comparar, selecciona modelos de la misma categoría."); return;
  }
  if (lista.length >= 3) { alert("Puedes comparar hasta tres modelos."); return; }
  guardar([...lista, {ref:p.ref, categoria:p.categoria, tipo:tipoDe(p)}]);
}
function datosVista() { return PRODUCTOS.filter(p => tipoDe(p) === vista); }
function opciones(id, valores, activo) {
  document.getElementById(id).innerHTML = valores.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join("");
  document.getElementById(id).value = activo;
}
function pintarFiltros() {
  opciones("categoryFilter", ["Todas", ...unico(datosVista().map(p => p.categoria)).sort((a,b) => a.localeCompare(b,"es"))], categoria);
  opciones("brandFilter", ["Todas", ...unico(datosVista().map(p => p.marca)).sort((a,b) => a.localeCompare(b,"es"))], marca);
}
function filtrados() {
  const q = termino.trim().toLocaleLowerCase("es");
  return datosVista().filter(p => {
    if (categoria !== "Todas" && p.categoria !== categoria) return false;
    if (marca !== "Todas" && p.marca !== marca) return false;
    return !q || `${p.nombre} ${p.marca} ${p.categoria} ${p.modelo} ${p.ref}`.toLocaleLowerCase("es").includes(q);
  }).sort((a,b) => orden === "marca" ? a.marca.localeCompare(b.marca,"es") || a.nombre.localeCompare(b.nombre,"es") : a.nombre.localeCompare(b.nombre,"es"));
}
function card(p) {
  const foto = p.imagenes && p.imagenes[0];
  const thumb = foto ? `<img src="${esc(foto)}" alt="${esc(p.nombre)}" loading="lazy" decoding="async" onerror="imgFail(this)">` : ICON;
  const facts = (p.datos_clave || []).map(x => `<li>${esc(x)}</li>`).join("");
  const selected = seleccion().some(x => x.ref === p.ref);
  return `<article class="card"><a class="card-link" href="${esc(p.ficha)}" aria-label="Ver ficha técnica de ${esc(p.nombre)}"><div class="thumb">${thumb}</div><div class="card-body"><span class="nameplate">${esc(p.marca)}</span><h3>${esc(p.nombre)}</h3><span class="card-code">${p.modelo ? `Modelo ${esc(p.modelo)} · ` : ""}Código ${esc(p.ref)}</span>${facts ? `<ul class="card-facts">${facts}</ul>` : '<p class="card-facts pendiente">Consulta las características en la ficha</p>'}<span class="ask">Ver ficha técnica →</span></div></a><button type="button" class="compare-add" data-ref="${esc(p.ref)}" aria-pressed="${selected}" aria-label="${selected ? "Quitar" : "Agregar"} ${esc(p.nombre)} ${selected ? "de" : "a"} comparación">${selected ? "✓ En comparación" : "+ Comparar"}</button></article>`;
}
function referenceCard(p) {
  const selected = seleccion().some(x => x.ref === p.ref);
  return `<article class="reference-card"><a href="${esc(p.ficha)}"><span class="reference-meta">${esc(p.categoria)}</span><h3>${esc(p.nombre)}</h3><span class="reference-code">Código: ${esc(p.ref)}</span><span class="reference-action">Ver ficha y consultar detalles →</span></a><button type="button" class="compare-add" data-ref="${esc(p.ref)}" aria-pressed="${selected}" aria-label="${selected ? "Quitar" : "Agregar"} ${esc(p.nombre)} ${selected ? "de" : "a"} comparación">${selected ? "✓ En comparación" : "+ Comparar"}</button></article>`;
}
function renderGrid() {
  const lista = filtrados(), visibles = lista.slice(0, limite);
  document.getElementById("grid").innerHTML = visibles.filter(p => p.imagenes && p.imagenes[0]).map(card).join("");
  const solo = visibles.filter(p => !(p.imagenes && p.imagenes[0]));
  document.getElementById("referenceGrid").innerHTML = solo.map(referenceCard).join("");
  document.getElementById("referenceOnly").hidden = !solo.length;
  document.getElementById("empty").hidden = !!lista.length;
  document.getElementById("showMore").hidden = visibles.length >= lista.length;
  document.getElementById("count").textContent = `${lista.length} ${vista === "productos" ? "productos" : "accesorios y repuestos"}${visibles.length < lista.length ? ` · mostrando ${visibles.length}` : ""}`;
}
function cambiarVista(nueva) {
  vista = nueva; categoria = "Todas"; marca = "Todas"; termino = ""; limite = CANTIDAD_INICIAL;
  document.getElementById("q").value = "";
  document.querySelectorAll("#catalogTabs .tab").forEach(tab => tab.setAttribute("aria-selected", String(tab.dataset.vista === vista)));
  pintarFiltros(); renderGrid();
}
function mostrarMeta(meta) {
  const el = document.getElementById("catalogMeta");
  const fecha = Date.parse(meta && meta.fuente_stock_actualizado_utc);
  if (!Number.isFinite(fecha)) { el.textContent = "Confirma la disponibilidad y el precio con la tienda."; return; }
  el.textContent = `Señal de despacho consultada el ${new Intl.DateTimeFormat("es-CL",{timeZone:"America/Santiago",dateStyle:"long",timeStyle:"short"}).format(fecha)}. Si han pasado 24 horas, la ficha solo invita a consultar a tienda.`;
}
async function cargar() {
  try {
    const integrado = location.protocol === "file:" && Array.isArray(window.OLB_PRODUCTOS);
    const [datos, meta] = integrado ? [window.OLB_PRODUCTOS, window.OLB_CATALOGO_META] : await Promise.all([
      fetch("feed/catalogo_publico.json",{cache:"no-cache"}).then(r => {if(!r.ok) throw Error("Sin catálogo"); return r.json();}),
      fetch("feed/catalogo_publico_meta.json",{cache:"no-cache"}).then(r => r.json()).catch(() => null),
    ]);
    if (!Array.isArray(datos) || !datos.length) throw Error("Catálogo vacío");
    PRODUCTOS = datos; document.getElementById("loading").hidden = true;
    mostrarMeta(meta); pintarFiltros(); pintarComparacion(); renderGrid();
  } catch (error) {
    console.error(error); document.getElementById("loading").hidden = true;
    document.getElementById("empty").hidden = false;
    document.getElementById("empty").innerHTML = `<b>No pudimos cargar el catálogo</b><p>Llama a tienda al ${CONFIG.telefonoTexto} para consultar.</p>`;
  }
}
for (const id of ["storeMap","footMap","mapTop","heroMap"]) document.getElementById(id).href = CONFIG.maps;
document.getElementById("footMap").textContent = CONFIG.direccion;
document.getElementById("storeText").textContent = CONFIG.direccion;
document.getElementById("phoneTop").href = `tel:${CONFIG.telefono}`;
document.getElementById("q").addEventListener("input", e => {termino=e.target.value;limite=CANTIDAD_INICIAL;renderGrid();});
document.getElementById("categoryFilter").addEventListener("change",e => {categoria=e.target.value;limite=CANTIDAD_INICIAL;renderGrid();});
document.getElementById("brandFilter").addEventListener("change",e => {marca=e.target.value;limite=CANTIDAD_INICIAL;renderGrid();});
document.getElementById("sortOrder").addEventListener("change",e => {orden=e.target.value;renderGrid();});
document.getElementById("showMore").addEventListener("click",() => {limite+=CANTIDAD_INICIAL;renderGrid();});
document.querySelectorAll("#catalogTabs .tab").forEach(tab => tab.addEventListener("click",() => cambiarVista(tab.dataset.vista)));
for (const id of ["grid","referenceGrid"]) document.getElementById(id).addEventListener("click",e => {
  const boton = e.target.closest(".compare-add"); if (!boton) return;
  const p = PRODUCTOS.find(x => x.ref === boton.dataset.ref); if (p) alternarComparacion(p);
});
document.getElementById("compareClear").addEventListener("click",() => guardar([]));
cargar();
