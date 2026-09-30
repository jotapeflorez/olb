#!/usr/bin/env python3
"""Empaqueta solo la web y las fichas validadas; excluye fuentes operativas."""

import json
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ESTATICOS = (
    "index.html", "404.html", "catalogo.js", "comparar.html", "comparar.css", "comparar.js",
    "ficha.css", "ficha.js", "OLB_LOGO_OFICIAL_2026_SAN_PEDRO_ELECTROLUX_MADEMSA.png", "fachada-olb.webp",
)
FEED_PUBLICO = ("catalogo_publico.json", "catalogo_publico.js", "catalogo_publico_meta.json", "stock.json")
SKU = re.compile(r"[A-Z0-9+]+")


def copiar(origen, destino):
    assert origen.is_file() and not origen.is_symlink() and origen.stat().st_size, f"Archivo inválido: {origen}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, destino)


def main(artefacto, salida):
    artefacto = Path(artefacto).resolve(strict=True)
    salida = Path(salida).resolve()
    assert salida != BASE and BASE in salida.parents, "El destino debe ser una carpeta temporal del repositorio"
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    feed = json.loads((artefacto / "feed/catalogo_publico.json").read_text(encoding="utf-8"))
    refs = [str(fila.get("ref") or "").strip().upper() for fila in feed]
    assert len(refs) >= 50 and len(refs) == len(set(refs)) and all(SKU.fullmatch(ref) for ref in refs)
    meta = json.loads((artefacto / "feed/catalogo_publico_meta.json").read_text(encoding="utf-8"))
    stock = json.loads((artefacto / "feed/stock.json").read_text(encoding="utf-8"))
    assert meta["productos"] == len(refs)
    assert meta["fuente_stock_actualizado_utc"] == stock["actualizado_utc"]

    for nombre in ESTATICOS:
        copiar(BASE / nombre, salida / nombre)
    for nombre in FEED_PUBLICO:
        copiar(artefacto / "feed" / nombre, salida / "feed" / nombre)
    for ref in refs:
        copiar(artefacto / "p" / f"{ref}.html", salida / "p" / f"{ref}.html")
        copiar(artefacto / "feed/fichas" / f"{ref}.json", salida / "feed/fichas" / f"{ref}.json")
    assert len(list((salida / "p").glob("*.html"))) == len(refs)
    assert len(list((salida / "feed/fichas").glob("*.json"))) == len(refs)
    print(f"Paquete público preparado: {len(refs)} fichas; sin CSV, fuentes ni scripts internos")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python construir_publico.py ARTEFACTO DIST")
    main(sys.argv[1], sys.argv[2])
