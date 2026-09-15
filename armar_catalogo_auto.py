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
from datetime import datetime, timezone
from pathlib import Path

# Reutiliza funciones de TU extractor (debe estar junto a este archivo)
from extractor_olb import buscar_en_vtex, http_json, extraer_imagenes, obtener_url_ficha

# ------------------------- ajustes -------------------------
TIENDA = "https://www.totem.shopclub.cl"
MARCAS = {"electrolux", "fensa", "mademsa"}   # deja set() para incluir todas
IMG_LADO = 800          # imágenes cuadradas de 800x800 para que queden encuadradas
MAX_IMAGENES = 1        # la interfaz usa una imagen; no descargamos datos que no se muestran
PAGINA = 50             # tope de VTEX por consulta
PAUSA = 0.25            # pausa entre consultas
CATEGORIA_DEFECTO = "Electrohogar"
SALIDA = Path(__file__).parent / "productos.json"
SALIDA_META = Path(__file__).parent / "catalogo_meta.json"
SALIDA_JS = Path(__file__).parent / "datos_catalogo.js"
VIGENTES = Path(__file__).parent / "vigentes.json"
FUENTES_CACHE = Path(__file__).parent / "fuentes_oficiales.json"

# Las APIs por cuenta permiten descargar los catálogos oficiales por lotes.
# Las URL públicas se usan únicamente como enlace de ficha para el usuario.
FUENTES_OFICIALES = [
    ("Electrolux", "https://electroluxcl.vtexcommercestable.com.br", "https://www.electrolux.cl"),
    ("Mademsa", "https://mademsacl.vtexcommercestable.com.br", "https://www.tiendamademsa.cl"),
    ("Fensa", "https://fensacl.vtexcommercestable.com.br", "https://www.fensa.cl"),
]

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
    ruta = (categorias_vtex or [""])[0]
    hoja = [t for t in (ruta or "").split("/") if t]
    if any(t.lower() in {"accesorios", "repuestos"} for t in hoja):
        return hoja[-1] if hoja else "Accesorios y repuestos"
    n = (nombre or "").lower()
    for patron, cat in CATEGORIAS:
        if re.search(patron, n):
            return cat
    return hoja[-1] if hoja else CATEGORIA_DEFECTO

def tipo_catalogo_de(categorias_vtex):
    texto = " ".join(categorias_vtex or []).lower()
    return "accesorios" if "/accesorios/" in texto or "/repuestos/" in texto else "productos"

# Detecta garantías y servicios que NO deben aparecer como artículos del catálogo.
PATRON_NO_CATALOGO = re.compile(
    r"garant|extendid|servicio t|instalaci|conexi[oó]n|visita|p[oó]liza|cobertura|plan de protecc",
    re.I,
)

def es_servicio_oculto(prod):
    texto = (prod.get("productName") or "") + " " + " ".join(prod.get("categories") or [])
    return bool(PATRON_NO_CATALOGO.search(texto))

def es_aire_acondicionado(prod):
    texto = " ".join([
        str(prod.get("productName") or ""),
        str(prod.get("productReference") or ""),
        " ".join(prod.get("categories") or []),
    ])
    return bool(re.search(r"aire acondicionado|split|eaix\d|eais\d|eaie\d", texto, re.I))

def es_kit_oculto(prod):
    """Oculta kits y referencias combinadas; solo admite conjuntos de aire acondicionado."""
    texto = " ".join([
        str(prod.get("productName") or ""),
        " ".join(prod.get("categories") or []),
    ])
    referencia_compuesta = any("+" in ref for ref in referencias_sku(prod))
    rotulado_como_kit = bool(re.search(r"\bkit(?:s)?\b|\bcombo\b|\bpack\b", texto, re.I))
    return (referencia_compuesta or rotulado_como_kit) and not es_aire_acondicionado(prod)

def normalizar_sku(valor):
    """Conserva el SKU como identificador de texto y normaliza solo el cruce."""
    texto = str(valor or "").strip().upper()
    return re.sub(r"\s+", "", texto)

def cargar_vigentes():
    if not VIGENTES.exists():
        raise RuntimeError("Falta vigentes.json; no se puede aplicar la regla comercial del catálogo.")
    datos = json.loads(VIGENTES.read_text(encoding="utf-8-sig"))
    salida = {}
    for fila in datos:
        sku = normalizar_sku(fila.get("sku") if isinstance(fila, dict) else fila)
        if sku and sku not in salida:
            salida[sku] = fila if isinstance(fila, dict) else {"sku": sku}
    if not salida:
        raise RuntimeError("vigentes.json no contiene SKU válidos.")
    return salida

def referencias_sku(prod):
    referencias = []
    for valor in (prod.get("productReference"), prod.get("productId")):
        sku = normalizar_sku(valor)
        if sku:
            referencias.append(sku)
    for item in prod.get("items") or []:
        for referencia in item.get("referenceId") or []:
            if isinstance(referencia, dict):
                sku = normalizar_sku(referencia.get("Value") or referencia.get("value"))
                if sku:
                    referencias.append(sku)
        for clave in ("itemId", "ean"):
            sku = normalizar_sku(item.get(clave))
            if sku:
                referencias.append(sku)
    return list(dict.fromkeys(referencias))

def referencia_principal(prod, vigentes_skus):
    referencias = referencias_sku(prod)
    return next((sku for sku in referencias if sku in vigentes_skus), referencias[0] if referencias else "")

def componentes_referencia_compuesta(prod):
    """Separa referencias de conjuntos VTEX, por ejemplo SKU_INTERIOR+SKU_EXTERIOR."""
    componentes = []
    for referencia in referencias_sku(prod):
        if "+" not in referencia:
            continue
        for parte in referencia.split("+"):
            sku = normalizar_sku(parte)
            if sku:
                componentes.append(sku)
    return list(dict.fromkeys(componentes))

def categoria_vigente(fila):
    categoria = str(fila.get("categoria") or "").strip()
    return categoria.title() if categoria else CATEGORIA_DEFECTO

def tipo_vigente(fila):
    texto = f"{fila.get('categoria', '')} {fila.get('subcategoria', '')}".lower()
    return "accesorios" if re.search(r"accesorio|repuesto", texto) else "productos"

def modelo_vigente(fila):
    """Obtiene el modelo escrito en la descripción sin inventar un dato nuevo."""
    descripcion = str(fila.get("descripcion") or "").upper()
    candidatos = re.findall(r"\b[A-Z][A-Z0-9.-]*\d[A-Z0-9.-]*\b", descripcion)
    return candidatos[-1] if candidatos else ""

def imagenes_componente(modelo, fuente):
    """Usa solo la vista explícita de la unidad interior o exterior del conjunto."""
    if not fuente:
        return []
    modelo = (modelo or "").upper()
    vista = "interior" if modelo.startswith("EAIS") else "exterior" if modelo.startswith("EAIE") else ""
    if not vista:
        return []
    return [url for url in fuente.get("imagenes") or [] if vista in url.lower()][:1]

def respaldo_vigente(sku, fila, fuente_componente=None, fuente_oficial=None):
    """Registro mínimo para un SKU vigente que Tótem no publica en su API."""
    fuente_oficial = fuente_oficial or {}
    modelo = str(fuente_oficial.get("modelo") or fila.get("modelo") or modelo_vigente(fila)).strip()
    imagenes_verificadas = fuente_oficial.get("imagenes") or fila.get("imagenes") or []
    imagenes = list(imagenes_verificadas)[:1] or imagenes_componente(modelo, fuente_componente)
    marca = str(
        fuente_oficial.get("marca") or fila.get("marca") or
        (fuente_componente or {}).get("marca") or ""
    ).strip()
    url = str(
        fuente_oficial.get("url") or fila.get("url") or
        (fuente_componente or {}).get("url") or ""
    ).strip()
    fuente = (
        str(fuente_oficial.get("fuente") or fila.get("fuente_oficial") or "Ficha oficial del fabricante")
        if imagenes_verificadas else
        "Listado vigente San Pedro + imagen oficial del conjunto"
        if imagenes else
        "Listado vigente San Pedro"
    )
    return {
        "id": f"vigente-{sku}",
        "ref": sku,
        "modelo": modelo,
        "nombre": str(fila.get("descripcion") or sku).strip(),
        "marca": marca,
        "categoria": categoria_vigente(fila),
        "tipo_catalogo": tipo_vigente(fila),
        "despacho_disponible": False,
        "vigente": True,
        "precio": None,
        "dimensiones": fuente_oficial.get("dimensiones") or {},
        "imagenes": imagenes,
        "url": url,
        "fuente_datos": fuente,
    }

def cuadrar(url, lado=IMG_LADO):
    # inserta el resize cuadrado de VTEX: .../ids/123/... -> .../ids/123-800-800/...
    return re.sub(r"(/arquivos/ids/\d+)(?=/)", rf"\1-{lado}-{lado}", url)

def disponible_de(prod):
    for it in prod.get("items") or []:
        for s in it.get("sellers") or []:
            if (s.get("commertialOffer") or {}).get("AvailableQuantity", 0) > 0:
                return True
    return False

def precio_de(prod):
    """Precio vigente más bajo publicado, usado únicamente para ordenar."""
    precios = []
    for it in prod.get("items") or []:
        for seller in it.get("sellers") or []:
            oferta = seller.get("commertialOffer") or {}
            try:
                precio = float(oferta.get("Price") or 0)
            except (TypeError, ValueError):
                precio = 0
            if precio > 0:
                precios.append(precio)
    return min(precios) if precios else None

def valor_especificacion(prod, *nombres):
    """Devuelve el primer valor no vacío de una especificación VTEX."""
    for nombre in nombres:
        valor = prod.get(nombre)
        if isinstance(valor, list):
            valor = next((str(v).strip() for v in valor if str(v).strip()), "")
        elif valor is not None:
            valor = str(valor).strip()
        if valor:
            return valor
    return ""

def dimensiones_de(prod):
    """Extrae solo dimensiones verificables publicadas por Tótem/VTEX."""
    dimensiones = {
        "alto": valor_especificacion(
            prod, "Altura (Centímetros)", "Alto producto", "Altura producto", "Alto"
        ),
        "ancho": valor_especificacion(
            prod, "Ancho (Centímetros)", "Ancho producto", "Ancho"
        ),
        "profundidad": valor_especificacion(
            prod, "Profundidad (Centímetros)", "Profundidad producto", "Profundidad"
        ),
    }
    return {clave: valor for clave, valor in dimensiones.items() if valor}

def arbol_categorias():
    try:
        arbol = http_json(f"{TIENDA}/api/catalog_system/pub/category/tree/50")
    except Exception:
        arbol = []
    categorias = []
    def rec(nodos):
        for n in nodos or []:
            categorias.append(n.get("id"))
            hijos = n.get("children") or []
            rec(hijos)
    rec(arbol)
    categorias = list(dict.fromkeys(c for c in categorias if c))
    if not categorias:
        raise RuntimeError("Tótem no devolvió categorías; se conserva el último catálogo válido.")
    return categorias

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

def cargar_fuentes_cache():
    if not FUENTES_CACHE.exists():
        return {}
    try:
        datos = json.loads(FUENTES_CACHE.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        normalizar_sku(sku): fila
        for sku, fila in (datos.items() if isinstance(datos, dict) else [])
        if normalizar_sku(sku) and isinstance(fila, dict)
    }

def catalogo_oficial_por_lotes(api_base):
    """Descarga una tienda oficial en páginas de 50 registros."""
    salida = []
    for desde in range(0, 2500, PAGINA):
        hasta = desde + PAGINA - 1
        lote = http_json(
            f"{api_base.rstrip('/')}/api/catalog_system/pub/products/search"
            f"?_from={desde}&_to={hasta}"
        )
        if not isinstance(lote, list) or not lote:
            break
        salida.extend(lote)
        if len(lote) < PAGINA:
            break
        time.sleep(PAUSA)
    return salida

def url_publica_oficial(base_publica, prod):
    link_text = str(prod.get("linkText") or "").strip("/")
    return f"{base_publica.rstrip('/')}/{link_text}/p" if link_text else ""

def ficha_oficial(sku, prod, marca, base_publica):
    imagenes = []
    for imagen in extraer_imagenes(prod):
        url = imagen.get("url_original") or imagen.get("url_vtex")
        if url:
            imagenes.append(cuadrar(url))
            break
    return {
        "sku": sku,
        "marca": marca,
        "modelo": valor_especificacion(prod, "Modelo", "Modelo comercial", "Código modelo"),
        "nombre": str(prod.get("productName") or "").strip(),
        "dimensiones": dimensiones_de(prod),
        "imagenes": imagenes,
        "url": url_publica_oficial(base_publica, prod),
        "fuente": f"Ficha oficial {marca}",
    }

def actualizar_fuentes_oficiales(vigentes_skus):
    """Cruza SKU exactos por lotes y conserva la última ficha válida si una tienda falla."""
    cache = {
        sku: fila for sku, fila in cargar_fuentes_cache().items()
        if sku in vigentes_skus
    }
    fuentes_ok = 0
    for marca, api_base, base_publica in FUENTES_OFICIALES:
        try:
            productos = catalogo_oficial_por_lotes(api_base)
        except Exception as error:
            print(f"  Aviso: no se pudo actualizar {marca}: {error}")
            continue
        fuentes_ok += 1
        encontrados = 0
        for prod in productos:
            if es_servicio_oculto(prod) or es_kit_oculto(prod):
                continue
            exactos = set(referencias_sku(prod)) & vigentes_skus
            for sku in exactos:
                ficha = ficha_oficial(sku, prod, marca, base_publica)
                if ficha["imagenes"]:
                    cache[sku] = ficha
                    encontrados += 1
        print(f"  {marca}: {len(productos)} fichas, {encontrados} SKU vigentes con imagen")
    if fuentes_ok:
        FUENTES_CACHE.write_text(
            json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    return cache

def producto_publico(item):
    """Entrega a la web solo los campos usados por la interfaz."""
    campos = (
        "id", "ref", "modelo", "nombre", "marca", "categoria", "tipo_catalogo",
        "despacho_disponible", "precio", "dimensiones", "imagenes",
    )
    return {campo: item.get(campo) for campo in campos}

def a_catalogo(prod, vigentes_skus):
    urls = []
    for im in extraer_imagenes(prod):          # <- tu extractor (URL original)
        u = im.get("url_original") or im.get("url_vtex")
        if u:
            u = cuadrar(u)
            if u not in urls:
                urls.append(u)
        if len(urls) >= MAX_IMAGENES:
            break
    nombre = prod.get("productName") or ""
    referencias = referencias_sku(prod)
    ref = referencia_principal(prod, vigentes_skus)
    coincidencias_vigentes = [sku for sku in referencias if sku in vigentes_skus]
    tipo_catalogo = tipo_catalogo_de(prod.get("categories"))
    return {
        "id": str(prod.get("productId") or ref or nombre),
        "ref": ref,
        "modelo": valor_especificacion(prod, "Modelo", "Modelo comercial", "Código modelo"),
        "nombre": nombre,
        "marca": prod.get("brand") or "",
        "categoria": categoria_de(nombre, prod.get("categories")),
        "tipo_catalogo": tipo_catalogo,
        "despacho_disponible": disponible_de(prod),
        "vigente": bool(coincidencias_vigentes),
        "precio": precio_de(prod),
        "dimensiones": dimensiones_de(prod),
        "imagenes": urls,
        "url": obtener_url_ficha(TIENDA, prod),
        "fuente_datos": "Tótem ShopClub",
    }

# ------------------------- principal -------------------------
def main():
    vigentes = cargar_vigentes()
    vigentes_skus = set(vigentes)
    print(f"Listado vigente San Pedro: {len(vigentes_skus)} SKU")
    print("Descubriendo categorías…")
    categorias = arbol_categorias()
    print(f"  {len(categorias)} categorías")

    por_id = {}          # catálogo OLB: vigente en archivo interno O con stock para despacho
    vigentes_encontrados = set()
    fuentes_componentes = {}
    servicios_omitidos = set()
    for cid in categorias:
        productos = productos_de_categoria(cid)
        for p in productos:
            pid = p.get("productId")
            if es_servicio_oculto(p) or es_kit_oculto(p):
                servicios_omitidos.add(str(pid or p.get("productReference") or p.get("productName")))
                continue
            if pid not in por_id:
                item = a_catalogo(p, vigentes_skus)
                # Algunos aires se publican como un conjunto SKU interior+SKU exterior.
                # Conservamos la vista oficial correspondiente para enriquecer cada SKU vigente.
                for sku_componente in componentes_referencia_compuesta(p):
                    if sku_componente in vigentes_skus:
                        fuentes_componentes.setdefault(sku_componente, item)
                es_accesorio = item["tipo_catalogo"] == "accesorios"
                marca_permitida = not MARCAS or (p.get("brand") or "").lower() in MARCAS
                vigentes_encontrados.update(set(referencias_sku(p)) & vigentes_skus)
                if not (item["vigente"] or item["despacho_disponible"]):
                    continue
                if not (marca_permitida or item["vigente"] or (es_accesorio and item["despacho_disponible"])):
                    continue
                por_id[pid] = item
        print(f"  cat {cid}: {len(productos)} productos ({len(por_id)} catálogo)")
        time.sleep(PAUSA)

    # La búsqueda por categorías puede omitir productos publicados en rutas incompletas.
    # Se consulta cada SKU vigente faltante porque la navegación puede omitir fichas publicadas.
    faltantes = [sku for sku in vigentes_skus if sku not in vigentes_encontrados]
    print(f"Buscando directamente {len(faltantes)} SKU vigentes no encontrados por categoría…")
    for posicion, sku in enumerate(faltantes, start=1):
        candidatos = buscar_en_vtex(TIENDA, sku)
        exacto = next((p for p in candidatos if sku in referencias_sku(p)), None)
        if exacto and not es_servicio_oculto(exacto) and not es_kit_oculto(exacto):
            item = a_catalogo(exacto, vigentes_skus)
            vigentes_encontrados.update(set(referencias_sku(exacto)) & vigentes_skus)
            por_id.setdefault(exacto.get("productId") or f"sku-{sku}", item)
        if posicion % 25 == 0:
            print(f"  {posicion}/{len(faltantes)} SKU revisados")
        time.sleep(PAUSA)

    print("Actualizando imágenes desde tiendas oficiales…")
    fuentes_oficiales = actualizar_fuentes_oficiales(vigentes_skus)

    # Completa imágenes faltantes en registros encontrados por Tótem sin alterar su stock.
    for item in por_id.values():
        sku = normalizar_sku(item.get("ref"))
        fuente = fuentes_oficiales.get(sku)
        if fuente and not item.get("imagenes"):
            item["imagenes"] = list(fuente.get("imagenes") or [])[:1]
            item["modelo"] = item.get("modelo") or fuente.get("modelo") or ""
            item["marca"] = item.get("marca") or fuente.get("marca") or ""
            item["dimensiones"] = item.get("dimensiones") or fuente.get("dimensiones") or {}

    respaldos = 0
    for sku in sorted(vigentes_skus - vigentes_encontrados):
        fila = vigentes[sku]
        descripcion = str(fila.get("descripcion") or "")
        if PATRON_NO_CATALOGO.search(descripcion):
            servicios_omitidos.add(sku)
            continue
        fuente = fuentes_oficiales.get(sku)
        prod_minimo = {"productName": descripcion, "productReference": sku, "categories": []}
        if es_kit_oculto(prod_minimo):
            servicios_omitidos.add(sku)
            continue
        por_id[f"vigente-{sku}"] = respaldo_vigente(
            sku, fila, fuentes_componentes.get(sku), fuente
        )
        respaldos += 1

    salida = sorted(
        por_id.values(),
        key=lambda x: (x["tipo_catalogo"], x["categoria"], x["nombre"]),
    )
    if not salida:
        raise RuntimeError("Tótem no devolvió productos válidos; se conserva el último catálogo válido.")
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    meta = {
        "actualizado_utc": ahora,
        "fuente_disponibilidad": "https://www.totem.shopclub.cl",
        "productos": len(salida),
        "disponibles_despacho": sum(1 for p in salida if p["despacho_disponible"]),
        "cantidad_productos": sum(1 for p in salida if p["tipo_catalogo"] == "productos"),
        "cantidad_accesorios_repuestos": sum(1 for p in salida if p["tipo_catalogo"] == "accesorios"),
        "vigentes_excel": len(vigentes_skus),
        "vigentes_encontrados_totem": len(vigentes_encontrados),
        "vigentes_con_respaldo_minimo": respaldos,
        "incluidos_solo_por_stock": sum(1 for p in salida if p["despacho_disponible"] and not p["vigente"]),
        "regla_publicacion": "vigente_interno_o_stock_totem",
    }
    salida_publica = [producto_publico(item) for item in salida]
    SALIDA.write_text(
        json.dumps(salida_publica, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    SALIDA_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    SALIDA_JS.write_text(
        "window.OLB_PRODUCTOS = " + json.dumps(salida_publica, ensure_ascii=False) + ";\n"
        "window.OLB_CATALOGO_META = " + json.dumps(meta, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"\nOK Catalogo informativo OLB: {len(salida)} productos -> {SALIDA.name}")
    print(f"OK Disponibilidad para despacho: {meta['disponibles_despacho']}")
    print(f"OK Productos: {meta['cantidad_productos']}")
    print(f"OK Accesorios y repuestos: {meta['cantidad_accesorios_repuestos']}")
    print(f"OK Vigentes encontrados en Tótem: {meta['vigentes_encontrados_totem']}")
    print(f"OK Vigentes con respaldo mínimo: {meta['vigentes_con_respaldo_minimo']}")
    print(f"OK Incluidos solo por stock: {meta['incluidos_solo_por_stock']}")
    print(f"OK Garantias/servicios omitidos del catalogo: {len(servicios_omitidos)}")
    print(f"OK Datos compatibles con apertura directa -> {SALIDA_JS.name}")

if __name__ == "__main__":
    main()
