#!/usr/bin/env python3
"""Genera un CSV liviano para OLB OS a partir del feed público validado.

No reemplaza VERIFY ni el catálogo maestro. Su objetivo es exponer a OLB OS
solo datos operativos seguros: referencia/SKU, nombre, marca, categoría,
disponibilidad, enlace de ficha oficial cuando existe, imagen principal y
fecha de sincronización.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
FEED_JSON = BASE / "feed" / "catalogo_publico.json"
META_JSON = BASE / "feed" / "catalogo_publico_meta.json"
FUENTES_JSON = BASE / "fuentes_oficiales.json"
SALIDA = BASE / "feed" / "catalogo_olb_os.csv"

CAMPOS = [
    "id",
    "ref",
    "nombre",
    "marca",
    "categoria",
    "disponible",
    "url",
    "imagen1",
    "imagen2",
    "imagen3",
    "imagen4",
    "fecha_sync",
]


def cargar_json(ruta: Path, defecto):
    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return defecto


def normalizar_ref(valor: object) -> str:
    return str(valor or "").strip().upper()


def main() -> None:
    productos = cargar_json(FEED_JSON, [])
    meta = cargar_json(META_JSON, {})
    fuentes = cargar_json(FUENTES_JSON, {})

    if not isinstance(productos, list) or not productos:
        raise RuntimeError("feed/catalogo_publico.json no contiene productos válidos")

    if not isinstance(fuentes, dict):
        fuentes = {}

    fuentes_normalizadas = {
        normalizar_ref(sku): ficha
        for sku, ficha in fuentes.items()
        if normalizar_ref(sku) and isinstance(ficha, dict)
    }

    fecha_sync = str(meta.get("actualizado_utc") or "").strip()
    filas = []

    for producto in productos:
        ref = normalizar_ref(producto.get("ref"))
        oficial = fuentes_normalizadas.get(ref, {})

        imagenes_feed = [
            str(url).strip()
            for url in (producto.get("imagenes") or [])
            if str(url).strip()
        ]
        imagenes_oficiales = [
            str(url).strip()
            for url in (oficial.get("imagenes") or [])
            if str(url).strip()
        ]

        imagenes = []
        for url in imagenes_oficiales + imagenes_feed:
            if url and url not in imagenes:
                imagenes.append(url)
            if len(imagenes) >= 4:
                break

        filas.append({
            "id": str(producto.get("id") or ref).strip(),
            "ref": ref,
            "nombre": str(producto.get("nombre") or oficial.get("nombre") or "").strip(),
            "marca": str(producto.get("marca") or oficial.get("marca") or "").strip(),
            "categoria": str(producto.get("categoria") or "").strip(),
            "disponible": "SI" if bool(producto.get("despacho_disponible")) else "NO",
            "url": str(oficial.get("url") or "").strip(),
            "imagen1": imagenes[0] if len(imagenes) > 0 else "",
            "imagen2": imagenes[1] if len(imagenes) > 1 else "",
            "imagen3": imagenes[2] if len(imagenes) > 2 else "",
            "imagen4": imagenes[3] if len(imagenes) > 3 else "",
            "fecha_sync": fecha_sync,
        })

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    temporal = SALIDA.with_suffix(".csv.tmp")
    with temporal.open("w", encoding="utf-8-sig", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=CAMPOS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)
    temporal.replace(SALIDA)

    con_url = sum(bool(fila["url"]) for fila in filas)
    con_imagen = sum(bool(fila["imagen1"]) for fila in filas)
    print(f"Feed OLB OS generado: {len(filas)} productos -> {SALIDA}")
    print(f"  Con URL oficial: {con_url}")
    print(f"  Con imagen: {con_imagen}")


if __name__ == "__main__":
    main()
