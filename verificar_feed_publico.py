#!/usr/bin/env python3
"""Comprueba que el feed público respete el control de publicación OLB."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE = Path(__file__).resolve().parent


def cargar(nombre: str):
    with (BASE / nombre).open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def sku(valor: object) -> str:
    return re.sub(r"[^A-Z0-9+]", "", str(valor or "").strip().upper())


def claves(fila: dict) -> set[str]:
    return {valor for valor in (sku(fila.get("sku_maestro")), sku(fila.get("sku_totem"))) if valor}


def main() -> None:
    control = cargar("publicacion_control.json")
    feed = cargar("feed/catalogo_publico.json")
    meta = cargar("feed/catalogo_publico_meta.json")

    refs = [sku(producto.get("ref")) for producto in feed]
    ids = [str(producto.get("id") or "").strip() for producto in feed]
    assert all(refs), "Hay fichas sin SKU"
    assert len(refs) == len(set(refs)), "Hay SKU duplicados"
    assert all(ids) and len(ids) == len(set(ids)), "Hay ID vacíos o duplicados"

    for producto in feed:
        assert str(producto.get("nombre") or "").strip(), f"Falta nombre en {producto.get('ref')}"
        assert str(producto.get("marca") or "").strip(), f"Falta marca en {producto.get('ref')}"
        assert str(producto.get("categoria") or "").strip(), f"Falta categoría en {producto.get('ref')}"
        assert producto.get("tipo_catalogo") in {"productos", "accesorios"}, f"Tipo inválido en {producto.get('ref')}"
        assert len(producto.get("imagenes") or []) == 1, f"Falta imagen principal en {producto.get('ref')}"

    bloqueados: set[str] = set()
    manual_publicar: set[str] = set()
    for fila in control.get("revision_manual", []):
        decision = str(fila.get("decision") or "Pendiente").strip().casefold()
        if decision in {"pendiente", "ocultar"}:
            bloqueados.update(claves(fila))
        elif decision == "publicar":
            manual_publicar.update(claves(fila))

    automaticos: set[str] = set()
    for fila in control.get("publicar_automatico", []):
        automaticos.update(claves(fila))

    refs_feed = set(refs)
    assert not (refs_feed & bloqueados), "El feed contiene SKU pendientes u ocultos"
    assert refs_feed <= (automaticos | manual_publicar), "El feed contiene SKU sin decisión publicable"
    assert int(meta.get("productos", -1)) == len(feed), "El total del metadato no coincide con el feed"
    assert int(meta.get("publicados_por_regla_automatica", -1)) + int(meta.get("publicados_por_revision_manual", -1)) == len(feed), "El origen de las publicaciones no cuadra"

    patron_servicio = re.compile(r"garant|extendid|servicio t|instalaci|conexi[oó]n|visita|p[oó]liza|cobertura|plan de protecc", re.I)
    patron_kit = re.compile(r"\bkit(?:s)?\b|\bcombo\b|\bpack\b", re.I)
    patron_aire = re.compile(r"aire acondicionado|\bsplit\b|eaix\d|eais\d|eaie\d", re.I)
    prohibidos = []
    for producto in feed:
        texto = f"{producto.get('nombre') or ''} {producto.get('categoria') or ''} {producto.get('ref') or ''}"
        if patron_servicio.search(texto) or ((patron_kit.search(texto) or "+" in str(producto.get("ref") or "")) and not patron_aire.search(texto)):
            prohibidos.append(producto.get("ref"))
    assert not prohibidos, f"El feed contiene servicios o packs no permitidos: {prohibidos}"

    print(f"Feed válido: {len(feed)} fichas únicas")
    print(f"  Pendientes u ocultas publicadas: {len(refs_feed & bloqueados)}")
    print(f"  Fichas sin imagen principal: {sum(not p.get('imagenes') for p in feed)}")
    print(f"  Servicios o packs no permitidos: {len(prohibidos)}")
    print(f"  Peso: {(BASE / 'feed/catalogo_publico.json').stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
