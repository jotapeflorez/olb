const ref = document.body.dataset.ref;
const categoria = document.body.dataset.categoria;
const tipo = document.body.dataset.tipo;
const STORAGE = "olb_comparar_v1";
const leer = () => { try { return JSON.parse(sessionStorage.getItem(STORAGE) || "[]"); } catch { return []; } };
function guardar(lista) { sessionStorage.setItem(STORAGE, JSON.stringify(lista)); pintarComparacion(); }
function pintarComparacion() {
  const lista = leer(), barra = document.getElementById("compareBar"), boton = document.getElementById("comparar");
  barra.hidden = !lista.length;
  document.getElementById("compareCount").textContent = `${lista.length} de 3 modelos`;
  boton.textContent = lista.some(x => x.ref === ref) ? "Quitar de comparación" : "Agregar a comparación";
  document.getElementById("compareLink").href = `../comparar.html?ref=${lista.map(x => encodeURIComponent(x.ref)).join(",")}`;
}
document.getElementById("comparar").addEventListener("click", () => {
  const lista = leer();
  if (lista.some(x => x.ref === ref)) { guardar(lista.filter(x => x.ref !== ref)); return; }
  if (lista.length && (lista[0].categoria !== categoria || lista[0].tipo !== tipo)) {
    alert("Para comparar, selecciona modelos de la misma categoría."); return;
  }
  if (lista.length >= 3) { alert("Puedes comparar hasta tres modelos."); return; }
  guardar([...lista, {ref, categoria, tipo}]);
});
document.getElementById("compareClear").addEventListener("click", () => guardar([]));
pintarComparacion();

fetch(`../feed/fichas/${encodeURIComponent(ref)}.json`).then(r => {
  if (!r.ok) throw new Error("Sin ficha"); return r.json();
}).then(ficha => {
  const miniaturas = document.getElementById("miniaturas");
  if (ficha.imagenes.length < 2) return;
  ficha.imagenes.forEach((url, index) => {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.setAttribute("aria-label", `Ver foto ${index + 1}`);
    boton.setAttribute("aria-current", String(index === 0));
    const img = document.createElement("img"); img.src = url; img.alt = ""; img.loading = "lazy";
    boton.append(img);
    boton.addEventListener("click", () => {
      const principal = document.getElementById("fotoPrincipal");
      if (principal) principal.src = url;
      miniaturas.querySelectorAll("button").forEach(b => b.setAttribute("aria-current", String(b === boton)));
    });
    miniaturas.append(boton);
  });
}).catch(() => {});

fetch("../feed/stock.json", {cache:"no-cache"}).then(r => {
  if (!r.ok) throw new Error("Sin stock"); return r.json();
}).then(stock => {
  const fecha = Date.parse(stock.actualizado_utc);
  const fresco = Number.isFinite(fecha) && Date.now() >= fecha && Date.now() - fecha < 24 * 60 * 60 * 1000;
  if (!fresco || !stock.disponibles.includes(ref)) return;
  const elemento = document.getElementById("stock");
  elemento.classList.add("fresco");
  elemento.querySelector("strong").textContent = "Tótem indica disponibilidad para despacho";
  elemento.querySelector("span").textContent = "Señal reciente; confirma stock, comuna y condiciones con la tienda antes de comprar.";
}).catch(() => {});
