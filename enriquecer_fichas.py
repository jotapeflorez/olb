#!/usr/bin/env python3
"""Completa fichas publicadas con el catálogo VTEX por referencia exacta.

Sirve para renovar los datos de una entrega existente sin alterar las reglas
de publicación ni la señal de stock. El recolector diario completo sigue en
armar_catalogo_auto.py.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from armar_catalogo_auto import (
    TIENDA, cuadrar, dimensiones_de, especificaciones_de, caracteristicas_de,
    http_json, imagenes_sku, normalizar_sku, referencias_sku, texto_plano,
    valor_especificacion,
)


BASE = Path(__file__).resolve().parent
PRODUCTOS = BASE / "productos.json"
PUBLICADOS = BASE / "feed" / "catalogo_publico.json"
PASO = 50
TOPE = 2500


def pedir_pagina(desde: int):
    url = f"{TIENDA}/api/catalog_system/pub/products/search?_from={desde}&_to={desde + PASO - 1}"
    return desde, http_json(url)


def pedir_id(pid: str):
    url = f"{TIENDA}/api/catalog_system/pub/products/search?fq=productId:{pid}"
    return pid, http_json(url)


def completar(registro: dict, producto: dict) -> bool:
    ref = normalizar_sku(registro.get("ref"))
    if ref not in referencias_sku(producto):
        return False
    imagenes = []
    for imagen in imagenes_sku(producto, ref):
        url = imagen.get("url_original") or imagen.get("url_vtex")
        if url and cuadrar(url) not in imagenes:
            imagenes.append(cuadrar(url))
        if len(imagenes) == 8:
            break
    nuevo = {
        "descripcion": texto_plano(producto.get("description"), 1200),
        "especificaciones": especificaciones_de(producto),
        "caracteristicas": caracteristicas_de(producto),
        "dimensiones": dimensiones_de(producto),
        "modelo": valor_especificacion(producto, "Modelo", "Modelo comercial", "Código modelo"),
        "imagenes": imagenes,
    }
    for campo in ("descripcion", "especificaciones", "caracteristicas", "dimensiones", "modelo"):
        if not registro.get(campo) and nuevo.get(campo):
            registro[campo] = nuevo[campo]
    if len(nuevo.get("imagenes") or []) > len(registro.get("imagenes") or []):
        registro["imagenes"] = nuevo["imagenes"]
    return True


def main():
    registros = json.loads(PRODUCTOS.read_text(encoding="utf-8"))
    publicados = {normalizar_sku(p["ref"]) for p in json.loads(PUBLICADOS.read_text(encoding="utf-8"))}
    por_sku = {normalizar_sku(p.get("ref")): p for p in registros if normalizar_sku(p.get("ref")) in publicados}
    vistos = set()
    fallas = []
    paginas = 0
    print(f"Buscando datos para {len(por_sku)} fichas publicadas en el catálogo VTEX…", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ejecutor:
        for inicio in range(0, TOPE, PASO * 8):
            futuros = [ejecutor.submit(pedir_pagina, desde) for desde in range(inicio, min(inicio + PASO * 8, TOPE), PASO)]
            cantidad = 0
            for futuro in as_completed(futuros):
                try:
                    _, productos = futuro.result()
                except Exception as error:
                    fallas.append(str(error))
                    continue
                if not isinstance(productos, list):
                    continue
                paginas += 1
                cantidad += len(productos)
                for producto in productos:
                    for ref in set(referencias_sku(producto)) & por_sku.keys():
                        if completar(por_sku[ref], producto):
                            vistos.add(ref)
            print(f"  {min(inicio + PASO * 8, TOPE)} posiciones: {len(vistos)} coincidencias exactas", flush=True)
            if cantidad == 0 and not fallas:
                break

        # La búsqueda global no incluye todas las fichas antiguas; consulta por
        # ID únicamente los SKU que ya estaban publicados y faltaron en ella.
        faltantes = {str(p.get("id")): ref for ref, p in por_sku.items() if ref not in vistos and str(p.get("id") or "").isdigit()}
        print(f"  {len(faltantes)} fichas adicionales por ID", flush=True)
        futuros = [ejecutor.submit(pedir_id, pid) for pid in faltantes]
        for posicion, futuro in enumerate(as_completed(futuros), 1):
            try:
                pid, productos = futuro.result()
                ref = faltantes[pid]
                if isinstance(productos, list):
                    for producto in productos:
                        if completar(por_sku[ref], producto):
                            vistos.add(ref)
                            break
            except Exception as error:
                fallas.append(str(error))
            if posicion % 25 == 0:
                print(f"  {posicion}/{len(faltantes)} ID consultados", flush=True)

    if len(vistos) < len(por_sku) // 2:
        raise RuntimeError(f"Solo se verificaron {len(vistos)} SKU; se conserva el archivo anterior")
    temporal = PRODUCTOS.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(registros, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporal.replace(PRODUCTOS)
    print(f"Actualizados {len(vistos)} SKU exactos; {len(fallas)} consultas fallidas; {paginas} páginas válidas.")


if __name__ == "__main__":
    main()
