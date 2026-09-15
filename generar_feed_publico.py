#!/usr/bin/env python3
"""Genera el feed público OLB desde el catálogo técnico y el control de publicación.

Este paso no modifica el catálogo visible. Escribe una salida independiente en
``feed/`` para poder revisarla antes de conectarla a ``index.html``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
PRODUCTOS = BASE / "productos.json"
CONTROL = BASE / "publicacion_control.json"
SALIDA = BASE / "feed"


def normalizar_sku(valor: object) -> str:
    """Normaliza sin destruir referencias compuestas de aire acondicionado."""
    texto = str(valor or "").strip().upper()
    return re.sub(r"[^A-Z0-9+]", "", texto)


def claves_fila(fila: dict) -> set[str]:
    return {
        clave
        for clave in (
            normalizar_sku(fila.get("sku_maestro")),
            normalizar_sku(fila.get("sku_totem")),
        )
        if clave
    }


def cargar_json(ruta: Path):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def escribir_json_atomico(ruta: Path, valor: object, *, compacto: bool) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    with temporal.open("w", encoding="utf-8", newline="\n") as archivo:
        if compacto:
            json.dump(valor, archivo, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(valor, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
    temporal.replace(ruta)


def categoria_publica(nombre: object, categoria: object) -> str:
    """Agrupa sinónimos de las fuentes para que el filtro no fragmente familias."""
    texto = f"{nombre or ''} {categoria or ''}".casefold()
    reglas = (
        (r"aire acondicionado|\bsplit\b", "Aire acondicionado"),
        (r"\bcampana", "Campanas"),
        (r"\bencimera", "Encimeras"),
        (r"\blavavajilla", "Lavavajillas"),
        (r"lavadora.?secadora|lavaseca|lavado y secado", "Lavasecadoras"),
        (r"\bsecadora", "Secadoras"),
        (r"\blavadora|centr[ií]fuga", "Lavadoras"),
        (r"\bfreezer|congelador", "Freezers"),
        (r"refrigerador|frigobar|enfriador", "Refrigeración"),
        (r"\bmicroondas", "Microondas"),
        (r"\bhorno", "Hornos"),
        (r"\bcocina", "Cocinas"),
        (r"\bcalefont", "Calefont"),
        (r"termo el[eé]ctrico|\btermos?\b", "Termos"),
        (r"\bestufa|calefactor", "Calefacción"),
        (r"aspirador|aspirado|floor care|barre alfombra", "Aspirado"),
    )
    for patron, destino in reglas:
        if re.search(patron, texto, re.IGNORECASE):
            return destino

    origen = str(categoria or "Producto").strip()
    equivalencias = {
        "Cocina": "Cocinas",
        "Refrigeradores": "Refrigeración",
        "Refrigeración": "Refrigeración",
        "Lavado": "Lavadoras",
        "Lavadoras Automaticas": "Lavadoras",
        "Lavadoras Semi-Automaticas": "Lavadoras",
        "Lavadoras Secadoras": "Lavasecadoras",
        "Lavado y Secado": "Lavasecadoras",
        "Freezer": "Freezers",
        "Floor Care": "Aspirado",
        "Utensílios": "Utensilios",
        "Centrifugas": "Lavadoras",
        "Olla eléctrica": "Ollas eléctricas",
        "Electrodomésticos": "Pequeños electrodomésticos",
        "Electrohogar": "Pequeños electrodomésticos",
    }
    return equivalencias.get(origen, origen or "Producto")


def producto_liviano(producto: dict) -> dict:
    imagenes = [str(url).strip() for url in producto.get("imagenes", []) if str(url).strip()]
    dimensiones = producto.get("dimensiones")
    if not isinstance(dimensiones, dict):
        dimensiones = {}
    dimensiones = {
        clave: str(valor).strip()
        for clave, valor in dimensiones.items()
        if clave in {"alto", "ancho", "profundidad"} and str(valor).strip()
    }
    precio = producto.get("precio")
    if not isinstance(precio, (int, float)) or isinstance(precio, bool) or precio <= 0:
        precio = None
    return {
        "id": str(producto.get("id") or producto.get("ref") or "").strip(),
        "ref": str(producto.get("ref") or "").strip(),
        "modelo": str(producto.get("modelo") or "").strip(),
        "nombre": str(producto.get("nombre") or "").strip(),
        "marca": str(producto.get("marca") or "").strip(),
        "categoria": categoria_publica(producto.get("nombre"), producto.get("categoria")),
        "tipo_catalogo": "accesorios" if producto.get("tipo_catalogo") == "accesorios" else "productos",
        "despacho_disponible": bool(producto.get("despacho_disponible")),
        "precio": precio,
        "dimensiones": dimensiones,
        "imagenes": imagenes[:1],
    }


def precio_control(valor: object):
    digitos = re.sub(r"[^0-9]", "", str(valor or ""))
    return int(digitos) if digitos else None


def producto_desde_control(fila: dict) -> dict:
    """Crea una ficha mínima con datos ya verificados en el informe de cruce."""
    ref = str(fila.get("sku_totem") or fila.get("sku_maestro") or "").strip()
    tipo = str(fila.get("tipo") or "").casefold()
    imagen = str(fila.get("imagen_oficial") or fila.get("imagen_totem") or "").strip()
    disponible = str(fila.get("disponible_despacho") or "").strip().casefold() in {"sí", "si", "true"}
    return {
        "id": f"control-{normalizar_sku(ref)}",
        "ref": ref,
        "modelo": "",
        "nombre": str(fila.get("nombre") or ref).strip(),
        "marca": str(fila.get("marca") or "").strip(),
        "categoria": categoria_publica(fila.get("nombre"), fila.get("familia")),
        "tipo_catalogo": "accesorios" if "accesorio" in tipo or "repuesto" in tipo else "productos",
        "despacho_disponible": disponible,
        "precio": precio_control(fila.get("precio_totem")),
        "dimensiones": {},
        "imagenes": [imagen] if imagen else [],
    }


PATRON_SERVICIO = re.compile(
    r"garant|extendid|servicio t|instalaci|conexi[oó]n|visita|p[oó]liza|cobertura|plan de protecc",
    re.IGNORECASE,
)
PATRON_KIT = re.compile(r"\bkit(?:s)?\b|\bcombo\b|\bpack\b", re.IGNORECASE)
PATRON_AIRE = re.compile(r"aire acondicionado|\bsplit\b|eaix\d|eais\d|eaie\d", re.IGNORECASE)


def razon_exclusion_dura(producto: dict) -> str:
    texto = f"{producto.get('nombre') or ''} {producto.get('categoria') or ''} {producto.get('ref') or ''}"
    if PATRON_SERVICIO.search(texto):
        return "servicio_garantia_instalacion"
    es_conjunto = bool(PATRON_KIT.search(texto) or "+" in str(producto.get("ref") or ""))
    if es_conjunto and not PATRON_AIRE.search(texto):
        return "kit_combo_pack_no_aire"
    return ""


def main() -> None:
    productos = cargar_json(PRODUCTOS)
    control = cargar_json(CONTROL)
    if not isinstance(productos, list) or not productos:
        raise RuntimeError("productos.json no contiene productos válidos")

    automaticos: set[str] = set()
    filas_automaticas = control.get("publicar_automatico", [])
    for fila in filas_automaticas:
        automaticos.update(claves_fila(fila))

    manual_por_sku: dict[str, set[str]] = {}
    filas_revision = control.get("revision_manual", [])
    for fila in filas_revision:
        decision = str(fila.get("decision") or "Pendiente").strip().lower()
        if decision not in {"pendiente", "publicar", "ocultar"}:
            decision = "pendiente"
        for clave in claves_fila(fila):
            manual_por_sku.setdefault(clave, set()).add(decision)

    publicados = []
    origen_por_sku: dict[str, str] = {}
    bloqueados_duros: set[str] = set()
    reconstruidos: list[dict] = []
    excluidos_regla_dura: list[dict] = []
    excluidos = {"pendiente": 0, "ocultar": 0, "sin_decision_publicable": 0}

    def incorporar(ficha: dict, sku: str, origen: str) -> bool:
        razon = razon_exclusion_dura(ficha)
        if razon:
            bloqueados_duros.add(sku)
            excluidos_regla_dura.append({"sku": ficha.get("ref", ""), "origen": origen, "razon": razon})
            return False
        publicados.append(ficha)
        origen_por_sku[sku] = origen
        return True

    for producto in productos:
        sku = normalizar_sku(producto.get("ref"))
        decisiones = manual_por_sku.get(sku, set())

        # La revisión manual tiene prioridad. Ante un conflicto, la regla es
        # conservadora: Ocultar > Pendiente > Publicar.
        if "ocultar" in decisiones:
            excluidos["ocultar"] += 1
            continue
        if "pendiente" in decisiones:
            excluidos["pendiente"] += 1
            continue
        if "publicar" in decisiones:
            incorporar(producto_liviano(producto), sku, "manual")
            continue
        if sku in automaticos:
            incorporar(producto_liviano(producto), sku, "automatico")
            continue

        excluidos["sin_decision_publicable"] += 1

    # Si una aprobación no existe en productos.json, no se descarta: se arma una
    # ficha mínima desde los datos verificados del informe de cruce.
    for fila in filas_revision:
        if str(fila.get("decision") or "Pendiente").strip().casefold() != "publicar":
            continue
        claves = claves_fila(fila)
        if any(clave in origen_por_sku or clave in bloqueados_duros for clave in claves):
            continue
        ficha = producto_desde_control(fila)
        sku = normalizar_sku(ficha["ref"])
        if not sku or sku in origen_por_sku:
            continue
        if incorporar(ficha, sku, "manual"):
            reconstruidos.append({"sku": ficha["ref"], "origen": "revision_manual"})

    for fila in filas_automaticas:
        claves = claves_fila(fila)
        if any(clave in origen_por_sku or clave in bloqueados_duros for clave in claves):
            continue
        if any(manual_por_sku.get(clave, set()) & {"ocultar", "pendiente"} for clave in claves):
            continue
        ficha = producto_desde_control(fila)
        sku = normalizar_sku(ficha["ref"])
        if not sku or sku in origen_por_sku:
            continue
        if incorporar(ficha, sku, "automatico"):
            reconstruidos.append({"sku": ficha["ref"], "origen": "regla_automatica"})

    publicados.sort(
        key=lambda p: (
            p["tipo_catalogo"],
            p["categoria"].casefold(),
            p["nombre"].casefold(),
            p["ref"],
        )
    )
    if not publicados:
        raise RuntimeError("El control no produjo ningún producto publicable")

    publicados_auto = {sku for sku, origen in origen_por_sku.items() if origen == "automatico"}
    publicados_manual = {sku for sku, origen in origen_por_sku.items() if origen == "manual"}

    actualizado = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    meta = {
        "actualizado_utc": actualizado,
        "fuente_control": control.get("fuente", {}).get("url", ""),
        "regla_publicacion": "publicar_automatico_mas_aprobacion_manual",
        "productos": len(publicados),
        "disponibles_despacho": sum(bool(p["despacho_disponible"]) for p in publicados),
        "cantidad_productos": sum(p["tipo_catalogo"] == "productos" for p in publicados),
        "cantidad_accesorios_repuestos": sum(p["tipo_catalogo"] == "accesorios" for p in publicados),
        "publicados_por_regla_automatica": len(publicados_auto),
        "publicados_por_revision_manual": len(publicados_manual),
        "aprobados_manualmente_en_control": control.get("conteos", {}).get("revision_publicar", 0),
        "excluidos_por_regla_dura": len(excluidos_regla_dura),
        "revision_pendiente": control.get("conteos", {}).get("revision_pendiente", 0),
        "revision_ocultar": control.get("conteos", {}).get("revision_ocultar", 0),
    }

    escribir_json_atomico(SALIDA / "catalogo_publico.json", publicados, compacto=True)
    escribir_json_atomico(SALIDA / "catalogo_publico_meta.json", meta, compacto=False)

    datos_js = (
        "window.OLB_PRODUCTOS = "
        + json.dumps(publicados, ensure_ascii=False, separators=(",", ":"))
        + ";\nwindow.OLB_CATALOGO_META = "
        + json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    js_tmp = (SALIDA / "catalogo_publico.js.tmp")
    js_tmp.write_text(datos_js, encoding="utf-8", newline="\n")
    js_tmp.replace(SALIDA / "catalogo_publico.js")

    auditoria = {
        "generado_utc": actualizado,
        "entrada_productos": len(productos),
        "salida_productos": len(publicados),
        "excluidos": excluidos,
        "fichas_reconstruidas_desde_control": reconstruidos,
        "fichas_reconstruidas_sin_imagen": [p["ref"] for p in publicados if p["id"].startswith("control-") and not p["imagenes"]],
        "excluidos_por_regla_dura": excluidos_regla_dura,
    }
    escribir_json_atomico(SALIDA / "auditoria_feed.json", auditoria, compacto=False)

    origen_bytes = PRODUCTOS.stat().st_size
    feed_bytes = (SALIDA / "catalogo_publico.json").stat().st_size
    reduccion = 100 * (1 - feed_bytes / origen_bytes)
    print(f"Feed generado: {len(publicados)} productos")
    print(f"  Regla automática: {len(publicados_auto)}")
    print(f"  Revisión manual: {len(publicados_manual)}")
    print(f"  Productos: {meta['cantidad_productos']}")
    print(f"  Accesorios y repuestos: {meta['cantidad_accesorios_repuestos']}")
    print(f"  Disponibles para despacho: {meta['disponibles_despacho']}")
    print(f"  Peso JSON: {feed_bytes:,} bytes ({reduccion:.1f}% menos que la entrada)")
    print(f"  Fichas reconstruidas desde el control: {len(reconstruidos)}")
    print(f"  Excluidos por regla permanente: {len(excluidos_regla_dura)}")


if __name__ == "__main__":
    main()
