#!/usr/bin/env python3
"""Completa datos faltantes con la API VTEX de la marca y SKU exacto."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

from armar_catalogo_auto import FUENTES_OFICIALES, ficha_oficial, http_json, referencias_sku


BASE = Path(__file__).resolve().parent
CACHE = BASE / "fuentes_oficiales.json"
API = {marca: (base, publica) for marca, base, publica in FUENTES_OFICIALES}


def buscar(ref, marca):
    base, publica = API[marca]
    productos = http_json(f"{base}/api/catalog_system/pub/products/search?ft={quote(ref)}")
    exacto = next((p for p in productos if ref in referencias_sku(p)), None)
    return ref, ficha_oficial(ref, exacto, marca, publica) if exacto else None


def main():
    raw = {p["ref"]: p for p in json.loads((BASE / "productos.json").read_text(encoding="utf-8"))}
    feed = json.loads((BASE / "feed/catalogo_publico.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    pendientes = []
    for p in feed:
        ref = p["ref"]
        origen, ficha = raw.get(ref, {}), cache.get(ref, {})
        fotos = max(len(origen.get("imagenes") or []), len(ficha.get("imagenes") or []))
        if (origen.get("especificaciones") or ficha.get("especificaciones")) and fotos > 1:
            continue
        marca = next((m for m in (origen.get("marca"), ficha.get("marca"), p.get("marca")) if m in API), "")
        if marca in API:
            pendientes.append((ref, marca))
    print(f"Consultando {len(pendientes)} SKU exactos en catálogos oficiales…", flush=True)
    encontrados = fallas = 0
    with ThreadPoolExecutor(max_workers=6) as ejecutor:
        futuros = [ejecutor.submit(buscar, ref, marca) for ref, marca in pendientes]
        for posicion, futuro in enumerate(as_completed(futuros), 1):
            try:
                ref, nuevo = futuro.result()
                if nuevo:
                    anterior = cache.get(ref, {})
                    for clave in ("modelo", "descripcion", "especificaciones", "caracteristicas", "dimensiones"):
                        if not nuevo.get(clave) and anterior.get(clave):
                            nuevo[clave] = anterior[clave]
                    if len(nuevo.get("imagenes") or []) < len(anterior.get("imagenes") or []):
                        nuevo["imagenes"] = anterior["imagenes"]
                    if nuevo["imagenes"]:
                        cache[ref] = nuevo
                        encontrados += 1
            except Exception:
                fallas += 1
            if posicion % 25 == 0:
                print(f"  {posicion}/{len(pendientes)}: {encontrados} fichas exactas", flush=True)
    temporal = CACHE.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporal.replace(CACHE)
    print(f"Verificadas {encontrados}; consultas fallidas {fallas}.")


if __name__ == "__main__":
    main()
