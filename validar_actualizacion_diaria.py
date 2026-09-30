#!/usr/bin/env python3
"""Impide reemplazar el catálogo vigente por una consulta incompleta."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent


def anterior(ruta):
    try:
        texto = subprocess.check_output(
            ["git", "show", f"HEAD:{ruta}"], cwd=BASE, text=True
        )
    except subprocess.CalledProcessError:
        return {}
    return json.loads(texto)


def main():
    origen = json.loads((BASE / "catalogo_meta.json").read_text(encoding="utf-8"))
    meta = json.loads((BASE / "feed/catalogo_publico_meta.json").read_text(encoding="utf-8"))
    previa = anterior("feed/catalogo_publico_meta.json")

    fecha = datetime.fromisoformat(origen["actualizado_utc"].replace("Z", "+00:00"))
    edad = (datetime.now(timezone.utc) - fecha).total_seconds()
    assert -300 <= edad <= 7200, "La señal de stock no proviene de esta ejecución"
    assert meta["fuente_stock_actualizado_utc"] == origen["actualizado_utc"], "Stock y consulta no coinciden"

    total = int(meta["productos"])
    despacho = int(meta["disponibles_despacho"])
    total_previo = int(previa.get("productos") or 0)
    despacho_previo = int(previa.get("disponibles_despacho") or 0)
    assert total >= 50, "La consulta produjo un catálogo anormalmente pequeño"
    if total_previo:
        assert total >= total_previo * 0.8, "Se perdió más del 20 % del catálogo; revisar fuentes"
        assert total <= total_previo * 1.25, "El catálogo creció más del 25 %; revisar decisiones"
    if despacho_previo:
        assert despacho >= despacho_previo * 0.25, "La fuente de despacho devolvió una caída anormal"
    print(f"Actualización diaria apta: {total} fichas, {despacho} con despacho; fuente hace {edad / 60:.0f} min")


if __name__ == "__main__":
    main()
