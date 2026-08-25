#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
armar_catalogo_auto.py — genera productos.json AUTOMÁTICAMENTE
==============================================================
Combina tu Extractor OLB con un descubrimiento automático de todo el
catálogo de la tienda. NO necesita lista de modelos: recorre solo la
tienda, arma las imágenes con la lógica de tu extractor y escribe
productos.json (el archivo que consume index.html).

Pensado para correr solo, 1 vez al día, en GitHub Actions.
No requiere instalar paquetes.

Uso manual:
    python armar_catalogo_auto.py
"""
from __future__ import annotations
import json, re, time
from pathlib import Path

# Reutiliza funciones de TU extractor (debe estar junto a este archivo)
from extractor_olb import http_json, extraer_imagenes

# ------------------------- ajustes -------------------------
TIENDA = "https://www.totem.shopclub.cl"
MARCAS = {"electrolux", "fensa", "mademsa"}   # deja set() para incluir todas
IMG_LADO = 800          # imágenes cuadradas de 800x800 para que queden encuadradas
MAX_IMAGENES = 4        # cuántas imágenes por producto
PAGINA = 50             # tope de VTEX por consulta
PAUSA = 0.25            # pausa entre consultas
CATEGORIA_DEFECTO = "Electrohogar"
SALIDA = Path(__file__).parent / "productos.json"

# Nombre del producto -> categoría limpia (evita que queden "sueltos")
CATEGORIAS = [
    (r"lavad|secad", "Lavado"),
    (r"refriger|frigo|freezer|side by side|no frost", "Refrigeración"),
    (r"cocina|horno|encimera|vitrocer|campana|anafe", "Cocina"),
    (r"aire acondicionado|climatiz|estufa|calefac|split|ventilad", "Climatización"),
    (r"microond|aspirad|cafeter|hervidor|licuad|batidora|plancha", "Electrohogar"),
]

# ------------------------- helpers -------------------------
def categoria_de(nombre, categorias_vtex):
    n = (nombre or "").lower()
    for patron, cat in CATEGORIAS:
        if re.search(patron, n):
            return cat
    ruta = (categorias_vtex or [""])[0]
    hoja = [t for t in (ruta or "").split("/") if t]
    return hoja[-1] if hoja else CATEGORIA_DEFECTO

# Detecta garantías / servicios que NO deben ir en el catálogo oficial
PATRON_GARANTIA = re.compile(r"garant|extendid|servicio t|instalaci|p[oó]liza|cobertura|plan de protecc", re.I)

def es_garantia(prod):
    texto = (prod.get("productName") or "") + " " + " ".join(prod.get("categories") or [])
    return bool(PATRON_GARANTIA.search(texto))

def cuadrar(url, lado=IMG_LADO):
    # inserta el resize cuadrado de VTEX: .../ids/123/... -> .../ids/123-800-800/...
    return re.sub(r"(/arquivos/ids/\d+)(?=/)", rf"\1-{lado}-{lado}", url)

def disponible_de(prod):
    for it in prod.get("items") or []:
        for s in it.get("sellers") or []:
            if (s.get("commertialOffer") or {}).get("AvailableQuantity", 0) > 0:
                return True
    return False

def arbol_categorias():
    try:
        arbol = http_json(f"{TIENDA}/api/catalog_system/pub/category/tree/50")
    except Exception:
        arbol = []
    hojas = []
    def rec(nodos):
        for n in nodos or []:
            hijos = n.get("children") or []
            if hijos:
                rec(hijos)
            else:
                hojas.append(n.get("id"))
    rec(arbol)
    return [h for h in hojas if h]

def productos_de_categoria(cid):
    out, frm = [], 0
    while frm < 2500:
        to = frm + PAGINA - 1
        url = f"{TIENDA}/api/catalog_system/pub/products/search?fq=C:{cid}&_from={frm}&_to={to}"
        try:
            lote = http_json(url)
        except Exception:
            break
        if not isinstance(lote, list) or not lote:
            break
        out.extend(lote)
        if len(lote) < PAGINA:
            break
        frm += PAGINA
        time.sleep(PAUSA)
    return out

def a_catalogo(prod):
    urls = []
    for im in extraer_imagenes(prod):          # <- tu extractor (URL original)
        u = im.get("url_original") or im.get("url_vtex")
        if u:
            u = cuadrar(u)
            if u not in urls:
                urls.append(u)
        if len(urls) >= MAX_IMAGENES:
            break
    if not urls:
        return None
    nombre = prod.get("productName") or ""
    ref = str(prod.get("productReference") or "")
    return {
        "id": str(prod.get("productId") or ref or nombre),
        "ref": ref,
        "nombre": nombre,
        "marca": prod.get("brand") or "",
        "categoria": categoria_de(nombre, prod.get("categories")),
        "disponible": disponible_de(prod),
        "imagenes": urls,
    }

# ------------------------- principal -------------------------
def main():
    print("Descubriendo categorías…")
    hojas = arbol_categorias()
    print(f"  {len(hojas)} categorías")

    por_id = {}          # catálogo oficial
    garantias = {}       # etiqueta aparte, fuera del catálogo
    for cid in hojas:
        productos = productos_de_categoria(cid)
        for p in productos:
            if MARCAS and (p.get("brand") or "").lower() not in MARCAS:
                continue
            pid = p.get("productId")
            if es_garantia(p):
                if pid not in garantias:
                    garantias[pid] = {
                        "id": str(pid or ""),
                        "ref": str(p.get("productReference") or ""),
                        "nombre": p.get("productName") or "",
                        "marca": p.get("brand") or "",
                        "categoria": "Garantía",
                    }
                continue
            if pid not in por_id:
                item = a_catalogo(p)
                if item:
                    por_id[pid] = item
        print(f"  cat {cid}: {len(productos)} productos ({len(por_id)} catálogo · {len(garantias)} garantías)")
        time.sleep(PAUSA)

    salida = sorted(por_id.values(), key=lambda x: (x["categoria"], x["nombre"]))
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    gar = sorted(garantias.values(), key=lambda x: x["nombre"])
    (SALIDA.parent / "garantias.json").write_text(
        json.dumps(gar, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ Catálogo oficial: {len(salida)} productos → {SALIDA.name}")
    print(f"✓ Garantías (aparte): {len(gar)} → garantias.json")

if __name__ == "__main__":
    main()
