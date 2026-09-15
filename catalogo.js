const CONFIG = {
  nombre: "Outlet Línea Blanca San Pedro",
  telefono: "+56412907387",
  telefonoTexto: "+56 41 290 7387",
  direccion: "Mall Arauco Premium Outlet, Local 38 · San Pedro de la Paz",
  maps: "https://www.google.com/maps/place/Outlet+Electrolux+Fensa+Mademsa/@-36.8667758,-73.1402856,663m/data=!3m2!1e3!4b1!4m6!3m5!1s0x9669c99e7bdefd17:0x5a189b5cb4a60b50!8m2!3d-36.8667801!4d-73.1377107!16s%2Fg%2F11v191nznj?entry=ttu&g_ep=EgoyMDI2MDkwMi4wIKXMDSoASAFQAw%3D%3D",
  heroTitulo: "Para tu hogar. Cerca de ti.",
  heroTexto: "Electrodomésticos, accesorios y repuestos Electrolux, Mademsa y Fensa.",
  heroApoyo: "Revisa nuestro catálogo, visítanos en San Pedro de la Paz o consulta por despacho a Chile continental.",
};

const ICON = {
  "Refrigeración": '<rect x="6" y="3" width="12" height="18" rx="2"/><path d="M6 10h12M9 6v2M9 13v3"/>',
  "Lavado": '<rect x="4" y="3" width="16" height="18" rx="2"/><circle cx="12" cy="13" r="4.5"/><path d="M7 6h.01M10 6h.01"/>',
  "Cocina": '<rect x="4" y="7" width="16" height="14" rx="2"/><path d="M4 11h16M8 3v3M12 3v3M16 3v3"/>',
  "Climatización": '<rect x="3" y="5" width="18" height="8" rx="2"/><path d="M6 17c0 1.5 1 2 1 3M12 17c0 1.5 1 2 1 3M18 17c0 1.5-1 2-1 3"/>',
};

const RE_NO_CATALOGO = /garant|extendid|servicio t|instalaci|conexi[oó]n|visita|p[oó]liza|cobertura|plan de protecc/i;
const RE_KIT = /\bkit(?:s)?\b|\bcombo\b|\bpack\b/i;
const CANTIDAD_INICIAL = 24;
const ARCHIVO_PRODUCTOS = "feed/catalogo_publico.json";
const ARCHIVO_META = "feed/catalogo_publico_meta.json";
const iconFor = categoria => {
  const nombre = (categoria || "").toLowerCase();
  const clave = /aire|climat|estufa|calef|ventil/.test(nombre)
    ? "Climatización"
    : Object.keys(ICON).find(k => nombre.includes(k.toLowerCase().slice(0, 4)));
  const dibujo = ICON[clave] || '<rect x="5" y="4" width="14" height="16" rx="2"/><circle cx="12" cy="12" r="3"/>';
  return `<svg class="ph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${dibujo}</svg>`;
};

let PRODUCTOS = [];
let vista = "productos";
let filtroCat = "Todas";
let filtroMarca = "Todas";
let termino = "";
let orden = "nombre";
let ultimoFoco = null;
let limiteVisible = CANTIDAD_INICIAL;

const primeraImg = p => (p.imagenes && p.imagenes[0]) || p.imagen || null;
const uniq = arr => Array.from(new Set(arr.filter(Boolean)));
const esc = s => String(s == null ? "" : s)
  .replace(/&/g, "&amp;")
  .replace(/"/g, "&quot;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;");
const esServicioOculto = p => RE_NO_CATALOGO.test(`${p.nombre || ""} ${p.categoria || ""}`);
const esAireAcondicionado = p => /aire acondicionado|split|eaix\d|eais\d|eaie\d/i.test(`${p.nombre || ""} ${p.categoria || ""} ${p.ref || ""}`);
const esKitOculto = p => (RE_KIT.test(`${p.nombre || ""} ${p.categoria || ""}`) || String(p.ref || "").includes("+")) && !esAireAcondicionado(p);
const tipoCatalogoDe = p => p.tipo_catalogo === "accesorios" ? "accesorios" : "productos";
const dimensionesDe = p => p.dimensiones && typeof p.dimensiones === "object" ? p.dimensiones : {};
const despachoDisponible = p => Boolean(p.despacho_disponible ?? p.disponible);

function imgFail(el) {
  const categoria = el.getAttribute("data-cat") || "";
  const contenedor = el.parentNode;
  el.remove();
  contenedor.insertAdjacentHTML("beforeend", iconFor(categoria));
}

function categorias() {
  return ["Todas", ...uniq(datosVista().map(p => p.categoria)).sort((a, b) => a.localeCompare(b, "es"))];
}

function marcas() {
  return ["Todas", ...uniq(datosVista().map(p => p.marca)).sort((a, b) => a.localeCompare(b, "es"))];
}

function datosVista() {
  return PRODUCTOS.filter(p => tipoCatalogoDe(p) === vista);
}

function aplicaMarca() {
  document.title = `Catálogo · ${CONFIG.nombre}`;
  document.getElementById("heroTitle").textContent = CONFIG.heroTitulo;
  document.getElementById("heroSub").textContent = CONFIG.heroTexto;
  document.getElementById("heroSupport").textContent = CONFIG.heroApoyo;
  document.getElementById("storeText").textContent = CONFIG.direccion;
  document.getElementById("storeMap").href = CONFIG.maps;
  document.getElementById("footMap").href = CONFIG.maps;
  document.getElementById("footMap").textContent = CONFIG.direccion;
  document.getElementById("mapTop").href = CONFIG.maps;
  document.getElementById("heroMap").href = CONFIG.maps;
  document.getElementById("phoneTop").href = `tel:${CONFIG.telefono}`;
  document.getElementById("modal-call").href = `tel:${CONFIG.telefono}`;
  document.getElementById("modal-map").href = CONFIG.maps;
}

function llenarSelector(id, valores, activo) {
  const selector = document.getElementById(id);
  selector.innerHTML = valores.map(valor => `<option value="${esc(valor)}">${esc(valor)}</option>`).join("");
  selector.value = activo;
}

function pintarFiltros() {
  llenarSelector("categoryFilter", categorias(), filtroCat);
  llenarSelector("brandFilter", marcas(), filtroMarca);
}

function precioNumerico(p) {
  const precio = Number(p.precio);
  return Number.isFinite(precio) && precio > 0 ? precio : null;
}

function compararNombre(a, b) {
  return String(a.nombre || "").localeCompare(String(b.nombre || ""), "es", { sensitivity: "base" });
}

function filtrados() {
  const busqueda = termino.trim().toLowerCase();
  const lista = datosVista().filter(p => {
    if (filtroCat !== "Todas" && p.categoria !== filtroCat) return false;
    if (filtroMarca !== "Todas" && p.marca !== filtroMarca) return false;
    if (!busqueda) return true;
    const texto = `${p.nombre || ""} ${p.marca || ""} ${p.categoria || ""} ${p.modelo || ""} ${p.ref || ""}`.toLowerCase();
    return texto.includes(busqueda);
  });
  return lista.sort((a, b) => {
    if (orden === "nombre") return compararNombre(a, b);
    const precioA = precioNumerico(a);
    const precioB = precioNumerico(b);
    if (precioA == null && precioB == null) return compararNombre(a, b);
    if (precioA == null) return 1;
    if (precioB == null) return -1;
    const diferencia = orden === "precio_desc" ? precioB - precioA : precioA - precioB;
    return diferencia || compararNombre(a, b);
  });
}

function card(p) {
  const img = primeraImg(p);
  const marca = p.marca || p.categoria || "Producto";
  const thumb = img
    ? `<img src="${esc(img)}" alt="${esc(p.nombre)}" loading="lazy" decoding="async" data-cat="${esc(p.categoria)}" onerror="imgFail(this)" />`
    : iconFor(p.categoria);
  return `
    <a class="card product-open" href="#producto-${esc(p.id)}" data-id="${esc(p.id)}" aria-label="Ver detalles de ${esc(p.nombre)}">
      <div class="thumb">${thumb}</div>
      <div class="card-body">
        <span class="nameplate">${esc(marca)}</span>
        <h3>${esc(p.nombre)}</h3>
        <span class="ask">
          Ver detalles
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
        </span>
      </div>
    </a>`;
}

function referenceCard(p) {
  return `
    <a class="reference-card product-open" href="#producto-${esc(p.id)}" data-id="${esc(p.id)}" aria-label="Consultar detalles de ${esc(p.nombre)}">
      <span class="reference-meta">${esc(p.categoria || "Producto")}</span>
      <h3>${esc(p.nombre)}</h3>
      <span class="reference-code">Código: ${esc(p.ref || "No informado")}</span>
      <span class="reference-action">Consultar detalles →</span>
    </a>`;
}

function renderGrid() {
  const lista = filtrados();
  const visibles = lista.slice(0, limiteVisible);
  const conFicha = visibles.filter(p => Boolean(primeraImg(p)));
  const soloReferencia = visibles.filter(p => !primeraImg(p));
  document.getElementById("grid").innerHTML = conFicha.map(card).join("");
  const referenceOnly = document.getElementById("referenceOnly");
  document.getElementById("referenceGrid").innerHTML = soloReferencia.map(referenceCard).join("");
  referenceOnly.hidden = soloReferencia.length === 0;
  document.getElementById("empty").hidden = lista.length > 0;
  document.getElementById("showMore").hidden = visibles.length >= lista.length;
  const unidad = vista === "productos"
    ? `producto${lista.length === 1 ? "" : "s"}`
    : (lista.length === 1 ? "accesorio o repuesto" : "accesorios y repuestos");
  const detalle = visibles.length < lista.length ? ` · mostrando ${visibles.length}` : "";
  document.getElementById("count").innerHTML = `<b>${lista.length}</b> ${unidad}${detalle}`;
}

function reiniciarCantidad() {
  limiteVisible = CANTIDAD_INICIAL;
}

function setVista(nuevaVista) {
  vista = nuevaVista;
  filtroCat = "Todas";
  filtroMarca = "Todas";
  termino = "";
  reiniciarCantidad();
  const input = document.getElementById("q");
  input.value = "";
  input.placeholder = vista === "productos"
    ? "Buscar productos por nombre, modelo o código…"
    : "Buscar accesorios o repuestos…";
  input.setAttribute("aria-label", vista === "productos" ? "Buscar productos" : "Buscar accesorios o repuestos");
  document.querySelectorAll("#catalogTabs .tab").forEach(tab => {
    tab.setAttribute("aria-selected", String(tab.dataset.vista === vista));
  });
  pintarFiltros();
  renderGrid();
}

async function cargarJSON(archivo) {
  const respuesta = await fetch(archivo, { cache: "no-cache" });
  if (!respuesta.ok) throw new Error(`No se pudo cargar ${archivo}`);
  return respuesta.json();
}

function mostrarMeta(meta) {
  const elemento = document.getElementById("catalogMeta");
  if (!meta || !meta.actualizado_utc) {
    elemento.textContent = "La disponibilidad de despacho se consulta dentro del detalle de cada producto.";
    return;
  }
  const fecha = new Date(meta.actualizado_utc);
  const texto = new Intl.DateTimeFormat("es-CL", {
    timeZone: "America/Santiago",
    dateStyle: "long",
    timeStyle: "short",
  }).format(fecha).replace(/\.$/, "");
  elemento.textContent = `Última actualización: ${texto}. La disponibilidad puede cambiar durante el día.`;
}

function mostrarError() {
  document.getElementById("loading").hidden = true;
  document.getElementById("count").textContent = "";
  document.getElementById("grid").innerHTML = "";
  const empty = document.getElementById("empty");
  empty.hidden = false;
  empty.innerHTML = `<div class="load-error"><b>No pudimos cargar el catálogo</b><p>Intenta nuevamente o llama a tienda para consultar los productos disponibles.</p><a class="btn btn-call" href="tel:${CONFIG.telefono}">Llamar al ${CONFIG.telefonoTexto}</a></div>`;
}

async function cargar() {
  try {
    const productosIntegrados = window.OLB_PRODUCTOS;
    const metaIntegrada = window.OLB_CATALOGO_META;
    const usarDatosIntegrados = window.location.protocol === "file:";
    const [productos, meta] = usarDatosIntegrados && Array.isArray(productosIntegrados) && productosIntegrados.length
      ? [productosIntegrados, metaIntegrada || null]
      : await Promise.all([
          cargarJSON(ARCHIVO_PRODUCTOS),
          cargarJSON(ARCHIVO_META).catch(() => null),
        ]);
    if (!Array.isArray(productos) || !productos.length) throw new Error("Catálogo vacío");
    PRODUCTOS = productos.filter(p => !esServicioOculto(p) && !esKitOculto(p));
    if (!PRODUCTOS.length) throw new Error("Catálogo sin productos válidos");
    document.getElementById("loading").hidden = true;
    mostrarMeta(meta);
    pintarFiltros();
    renderGrid();
  } catch (error) {
    console.error(error);
    mostrarError();
  }
}

function abrirModal(p, foco) {
  ultimoFoco = foco || document.activeElement;
  const img = primeraImg(p);
  const imgEl = document.getElementById("modal-img");
  const wrap = document.getElementById("modal-img-wrap");
  wrap.querySelectorAll(".ph").forEach(n => n.remove());
  if (img) {
    imgEl.src = img;
    imgEl.alt = p.nombre || "Producto";
    imgEl.hidden = false;
    imgEl.setAttribute("data-cat", p.categoria || "");
    imgEl.onerror = () => {
      imgEl.hidden = true;
      wrap.insertAdjacentHTML("beforeend", iconFor(p.categoria));
    };
  } else {
    imgEl.hidden = true;
    wrap.insertAdjacentHTML("beforeend", iconFor(p.categoria));
  }

  document.getElementById("modal-title").textContent = p.nombre || "";
  document.getElementById("modal-brand").textContent = p.marca || "Marca por confirmar en tienda";
  const identificacion = p.modelo
    ? `Modelo: ${p.modelo}${p.ref ? ` · Código: ${p.ref}` : ""}`
    : `Código / referencia: ${p.ref || "No informada"}`;
  document.getElementById("modal-ref").textContent = identificacion;

  const dimensiones = dimensionesDe(p);
  const datos = [
    ["Alto", dimensiones.alto],
    ["Ancho", dimensiones.ancho],
    ["Profundidad", dimensiones.profundidad],
  ];
  document.getElementById("modal-dimensions").innerHTML = datos.map(([nombre, valor]) => `
    <div class="dimension"><span>${nombre}</span><strong>${esc(valor || "No informada")}</strong></div>
  `).join("");
  const faltantes = datos.filter(([, valor]) => !valor).length;
  document.getElementById("modal-dimensions-note").textContent = faltantes
    ? "Las medidas no informadas deben confirmarse con la tienda antes de comprar."
    : "Confirma las medidas con la tienda antes de comprar.";

  const disponibilidad = document.getElementById("modal-availability");
  if (despachoDisponible(p)) {
    disponibilidad.className = "availability available";
    disponibilidad.innerHTML = "<strong>Disponible para despacho</strong><p>La última actualización indica que disponemos de stock para despacho. Confirma siempre la disponibilidad con la tienda, porque puede cambiar durante el día.</p>";
  } else {
    disponibilidad.className = "availability consult";
    disponibilidad.innerHTML = "<strong>Consulta disponibilidad para despacho</strong><p>La última actualización no confirma stock para despacho. La tienda puede contar con disponibilidad en sala u otras alternativas; consúltanos antes de comprar.</p>";
  }

  const modal = document.getElementById("productModal");
  modal.style.display = "block";
  document.body.style.overflow = "hidden";
  document.getElementById("modalClose").focus();
}

function cerrarModal() {
  document.getElementById("productModal").style.display = "none";
  document.body.style.overflow = "";
  if (ultimoFoco && typeof ultimoFoco.focus === "function") ultimoFoco.focus();
}

function abrirPorId(id, foco) {
  const producto = PRODUCTOS.find(p => String(p.id) === String(id));
  if (producto) abrirModal(producto, foco);
}

document.getElementById("modalClose").addEventListener("click", cerrarModal);
window.addEventListener("click", event => {
  if (event.target === document.getElementById("productModal")) cerrarModal();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") cerrarModal();
});
["grid", "referenceGrid"].forEach(id => {
  document.getElementById(id).addEventListener("click", event => {
    const tarjeta = event.target.closest(".product-open");
    if (!tarjeta) return;
    event.preventDefault();
    abrirPorId(tarjeta.dataset.id, tarjeta);
  });
});
document.getElementById("q").addEventListener("input", event => {
  termino = event.target.value;
  reiniciarCantidad();
  renderGrid();
});
document.getElementById("categoryFilter").addEventListener("change", event => {
  filtroCat = event.target.value;
  reiniciarCantidad();
  renderGrid();
});
document.getElementById("brandFilter").addEventListener("change", event => {
  filtroMarca = event.target.value;
  reiniciarCantidad();
  renderGrid();
});
document.getElementById("sortOrder").addEventListener("change", event => {
  orden = event.target.value;
  reiniciarCantidad();
  renderGrid();
});
document.getElementById("showMore").addEventListener("click", () => {
  limiteVisible += CANTIDAD_INICIAL;
  renderGrid();
});
document.querySelectorAll("#catalogTabs .tab").forEach(tab => {
  tab.addEventListener("click", () => setVista(tab.dataset.vista));
});

aplicaMarca();
cargar();
