#!/usr/bin/env python3
"""Espera a que Cloudflare Pages sirva el feed generado en esta ejecución."""

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
META = Path(os.environ.get("OLB_FEED_META", BASE / "feed/catalogo_publico_meta.json"))
URL = "https://olbsanpedro.pages.dev/feed/catalogo_publico_meta.json"


def main():
    esperado = json.loads(META.read_text(encoding="utf-8"))
    fecha = esperado["fuente_stock_actualizado_utc"]
    ultima_respuesta = "sin respuesta"
    limite = time.monotonic() + 600
    while time.monotonic() < limite:
        try:
            peticion = Request(f"{URL}?revision={fecha}", headers={"Cache-Control": "no-cache", "User-Agent": "Mozilla/5.0 OLB-Catalogo/1.0"})
            with urlopen(peticion, timeout=10) as respuesta:
                publico = json.load(respuesta)
            ultima_respuesta = str(publico.get("fuente_stock_actualizado_utc"))
            if publico.get("fuente_stock_actualizado_utc") == fecha:
                assert publico.get("productos") == esperado.get("productos"), "Conteo público no coincide"
                print(f"Cloudflare Pages actualizado: {fecha}, {publico['productos']} fichas")
                return
        except (HTTPError, URLError, ValueError) as error:
            ultima_respuesta = str(error)
        restante = limite - time.monotonic()
        if restante > 0:
            time.sleep(min(20, restante))
    raise RuntimeError(f"Cloudflare Pages no mostró la versión diaria {fecha}; último resultado: {ultima_respuesta}")


if __name__ == "__main__":
    main()
