const STORAGE = "olb_comparar_v1";
const normal = s => String(s || "").replace(/[^A-Z0-9+]/gi, "").toUpperCase();
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const parametros = new URLSearchParams(location.search).get("ref");
let guardados = [];
try { guardados = JSON.parse(sessionStorage.getItem(STORAGE) || "[]"); } catch { /* nueva sesión */ }
const refs = (parametros ? parametros.split(",") : guardados.map(x => x.ref)).map(normal).filter(Boolean).slice(0,3);
const unicos = [...new Set(refs)];
const estado = document.getElementById("estado");
const tabla = document.getElementById("tabla");

function fila(nombre, productos, obtener) {
  const valores = productos.map(obtener);
  const distintos = new Set(valores.filter(Boolean).map(x => String(x).toLowerCase())).size > 1;
  return `<tr><th scope="row">${esc(nombre)}</th>${valores.map(v => `<td class="${distintos ? "diferencia" : ""} ${v ? "" : "sin-dato"}">${esc(v || "No informado")}</td>`).join("")}</tr>`;
}
function pintar(productos) {
  const familia = productos[0].categoria, tipo = productos[0].tipo_catalogo;
  if (productos.some(p => p.categoria !== familia || p.tipo_catalogo !== tipo)) throw new Error("Elige productos de la misma categoría para compararlos.");
  const columnas = productos.map(p => {
    const foto = p.imagenes[0] ? `<img class="comp-foto" src="${esc(p.imagenes[0])}" alt="${esc(p.nombre)}">` : "";
    return `<th scope="col">${foto}<p class="comp-nombre">${esc(p.nombre)}</p><p class="modelo">${esc(p.marca)} · ${esc(p.modelo || p.ref)}</p><a href="p/${encodeURIComponent(p.ref)}.html">Ver ficha completa →</a></th>`;
  });
  const filas = [
    fila("Modelo", productos, p => p.modelo),
    fila("Código", productos, p => p.ref),
    fila("Alto", productos, p => p.dimensiones.alto),
    fila("Ancho", productos, p => p.dimensiones.ancho),
    fila("Profundidad", productos, p => p.dimensiones.profundidad),
  ];
  const claves = [...new Set(productos.flatMap(p => Object.keys(p.especificaciones)))];
  const relevantes = claves.filter(k => !/alto|ancho|profundidad|embalado|peso bruto|duraci[oó]n|plazo soporte|certificado/i.test(k));
  const otros = claves.filter(k => !relevantes.includes(k));
  const seccion = (titulo, lista) => lista.length ? `<tr class="fila-titulo"><th colspan="${productos.length + 1}" scope="colgroup">${esc(titulo)}</th></tr>${lista.map(k => fila(k, productos, p => p.especificaciones[k])).join("")}` : "";
  tabla.innerHTML = `<table class="comparacion"><thead><tr><th scope="col">${esc(familia)}</th>${columnas.join("")}</tr></thead><tbody>${filas.join("")}${seccion("Características", relevantes)}${seccion("Otros datos publicados", otros)}</tbody></table>`;
  tabla.hidden = false; estado.hidden = true;
}
if (!unicos.length) {
  estado.innerHTML = 'Selecciona modelos desde el <a href="index.html">catálogo OLB</a> para compararlos.';
} else {
  Promise.all(unicos.map(ref => fetch(`feed/fichas/${encodeURIComponent(ref)}.json`).then(r => {
    if (!r.ok) throw new Error(`No existe una ficha publicada para ${ref}.`);
    return r.json();
  }))).then(pintar).catch(error => { estado.textContent = error.message; });
}
