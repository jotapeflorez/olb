#!/usr/bin/env python3
"""Instala solo los datos aprobados del artefacto diario, nunca código."""

import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
RAIZ = ("productos.json", "fuentes_oficiales.json", "catalogo_meta.json", "datos_catalogo.js")
FEED = (
    "catalogo_publico.json", "catalogo_publico.js", "catalogo_publico_meta.json",
    "stock.json", "calidad_fichas.json", "auditoria_feed.json", "catalogo_olb_os.csv",
)


def copiar(entrada, salida):
    assert entrada.is_file() and not entrada.is_symlink() and entrada.stat().st_size, f"Archivo inválido: {entrada.name}"
    salida.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(entrada, salida)


def main(origen):
    origen = Path(origen).resolve(strict=True)
    for nombre in RAIZ:
        copiar(origen / nombre, BASE / nombre)
    for nombre in FEED:
        copiar(origen / "feed" / nombre, BASE / "feed" / nombre)

    for carpeta, patron in (("p", "*.html"), ("feed/fichas", "*.json")):
        archivos = list((origen / carpeta).glob(patron))
        assert 50 <= len(archivos) <= 5000, f"Cantidad anormal de archivos en {carpeta}"
        assert all(archivo.is_file() and not archivo.is_symlink() for archivo in archivos)
        destino = BASE / carpeta
        destino.mkdir(parents=True, exist_ok=True)
        for viejo in destino.glob(patron):
            viejo.unlink()
        for archivo in archivos:
            copiar(archivo, destino / archivo.name)
    print("Artefacto diario instalado: solo datos, feed y fichas generadas")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python publicar_catalogo_diario.py RUTA_ARTEFACTO")
    main(sys.argv[1])
