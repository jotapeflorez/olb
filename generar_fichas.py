#!/usr/bin/env python3
"""Genera fichas OLB internas para SKU publicados y datos para el comparador."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from armar_catalogo_auto import texto_plano
from generar_feed_publico import normalizar_sku

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "p"
DATOS = BASE / "feed" / "fichas"


def cargar(nombre):
    return json.loads((BASE / nombre).read_text(encoding="utf-8"))


def e(valor):
    return html.escape(str(valor or ""), quote=True)


def limpiar(valor, limite=500):
    texto = texto_plano(valor, limite)
    return re.sub(r"https?://\S+", "", texto).strip()


def imagenes_de(*fuentes):
    imagenes = []
    for fuente in fuentes:
        for url in fuente.get("imagenes") or []:
            parsed = urlparse(str(url))
            if parsed.scheme == "https" and parsed.netloc and url not in imagenes:
                imagenes.append(url)
            if len(imagenes) >= 8:
                return imagenes
    return imagenes


def detalle(publico, raw, oficial):
    specs_raw = raw.get("especificaciones") or {}
    specs_oficial = oficial.get("especificaciones") or {}
    specs = {}
    for fuente in (specs_oficial, specs_raw):
        if not isinstance(fuente, dict):
            continue
        for clave, valor in fuente.items():
            nombre, texto = limpiar(clave, 100), limpiar(valor, 180)
            if nombre and texto and not re.search(r"manual|infogr[aá]f|precio|url|video|feature", nombre, re.I):
                specs[nombre] = texto
    caracteristicas = []
    for frase in (raw.get("caracteristicas") or oficial.get("caracteristicas") or []):
        texto = limpiar(frase, 250)
        if texto and texto not in caracteristicas:
            caracteristicas.append(texto)
    niveles = next((valor for clave, valor in specs.items() if "niveles de temperatura" in clave.casefold()), "")
    explicacion = ""
    if all(palabra in niveles.casefold() for palabra in ("refrigerar", "conservar", "congelar")):
        cantidad = re.match(r"\d+", niveles)
        explicacion = (
            "Permite elegir entre refrigerar, conservar o congelar"
            + (f" con {cantidad.group()} niveles de temperatura." if cantidad else ".")
        )
    return {
        "ref": publico["ref"],
        "nombre": publico["nombre"],
        "modelo": publico["modelo"],
        "marca": publico["marca"],
        "categoria": publico["categoria"],
        "tipo_catalogo": publico["tipo_catalogo"],
        "dimensiones": publico["dimensiones"],
        "datos_clave": publico.get("datos_clave") or [],
        "imagenes": imagenes_de(raw, oficial, publico),
        "descripcion": limpiar(raw.get("descripcion") or oficial.get("descripcion"), 1200),
        "caracteristicas": caracteristicas[:6],
        **({"explicacion": explicacion} if explicacion else {}),
        "especificaciones": specs,
        "fuentes": (["Catálogo Tótem por SKU"] if raw and not str(raw.get("id") or "").startswith("vigente-") else [])
                   + ([f"Catálogo oficial {limpiar(oficial.get('marca'), 40)} por SKU"] if oficial and specs_oficial else []),
    }


def ficha_html(p):
    ref, nombre = p["ref"], p["nombre"]
    titulo = f"{nombre} | Ficha OLB San Pedro"
    resumen = p["descripcion"][:155] or f"Características y medidas publicadas de {nombre}. Consulta disponibilidad en Outlet Línea Blanca San Pedro."
    imagenes = p["imagenes"]
    foto = f'<img id="fotoPrincipal" src="{e(imagenes[0])}" alt="{e(nombre)}" decoding="async">' if imagenes else '<div class="sin-foto">Imagen por confirmar en tienda</div>'
    datos = "".join(f'<li>{e(x)}</li>' for x in p["datos_clave"])
    dimensiones = "".join(f'<div><dt>{e(label)}</dt><dd>{e(p["dimensiones"][key])}</dd></div>' for key, label in (("alto", "Alto"), ("ancho", "Ancho"), ("profundidad", "Profundidad")) if p["dimensiones"].get(key))
    if not dimensiones:
        dimensiones = '<p class="empty-spec">Medidas aún no publicadas para este código. Consúltalas antes de comprar.</p>'
    especificaciones = "".join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in p["especificaciones"].items())
    if not especificaciones:
        especificaciones = '<p class="empty-spec">Aún no contamos con especificaciones verificadas para este código.</p>'
    caracteristicas = "".join(f'<li>{e(x)}</li>' for x in p["caracteristicas"])
    explicacion = f'\n<aside class="entender"><strong>¿Qué significa 3 en 1?</strong><p>{e(p["explicacion"])}</p></aside>' if p.get("explicacion") else ""
    description = f'<p>{e(p["descripcion"])}</p>' if p["descripcion"] else '<p>Esta ficha reúne los datos comprobados para el código indicado. Confirma las características faltantes con la tienda.</p>'
    fuentes = ", ".join(p["fuentes"]) or "Listado vigente OLB y control de publicación"
    imagen_social = f'<meta name="twitter:card" content="summary_large_image"><meta property="og:image" content="{e(imagenes[0])}">' if imagenes else ""
    return f'''<!doctype html>
<html lang="es-CL"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title><meta name="description" content="{e(resumen)}">
<meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(resumen)}">{imagen_social}
<link rel="stylesheet" href="../ficha.css"><script defer src="../ficha.js"></script></head>
<body data-ref="{e(ref)}" data-categoria="{e(p['categoria'])}" data-tipo="{e(p['tipo_catalogo'])}">
<header class="top"><div class="top-in"><a href="../index.html" class="logo" aria-label="Volver al catálogo OLB"><img src="../OLB_LOGO_OFICIAL_2026_SAN_PEDRO_ELECTROLUX_MADEMSA.png" alt="Outlet Línea Blanca San Pedro"></a><a class="call" href="tel:+56412907387">Llamar a tienda</a></div></header>
<main><nav class="migas" aria-label="Ruta"><a href="../index.html">Catálogo</a><span>›</span><span>{e(p['categoria'])}</span><span>›</span><span>{e(p['modelo'] or ref)}</span></nav>
<section class="producto"><div class="galeria"><div class="foto" id="foto">{foto}</div><div class="miniaturas" id="miniaturas" aria-label="Fotos del producto"></div><small>Imágenes de catálogo asociadas al código publicado. La exhibición puede variar.</small></div>
<div class="producto-info"><p class="etiqueta">{e(p['marca'])} · {e(p['categoria'])}</p><h1>{e(nombre)}</h1><p class="identidad">{f'Modelo {e(p["modelo"])} · ' if p['modelo'] else ''}Código {e(ref)}</p>
{f'<ul class="resumen">{datos}</ul>' if datos else '<p class="resumen vacio">Características principales por confirmar para este código.</p>'}{explicacion}
<div class="stock" id="stock" role="status"><strong>Consultar disponibilidad para despacho</strong><span>La tienda confirma stock y condiciones antes de comprar.</span></div>
<p class="comercial">Compra presencial en San Pedro de la Paz o consulta despacho a Chile continental. Precio y condiciones se confirman con la tienda.</p>
<div class="acciones"><a class="primaria" href="tel:+56412907387">Llamar al +56 41 290 7387</a><button id="comparar" class="secundaria" type="button">Agregar a comparación</button></div>
<p class="direccion">Mall Arauco Premium Outlet · Local 38 · San Pedro de la Paz</p></div></section>
<div class="secciones"><section class="panel"><p class="sobre">Conoce el producto</p><h2>Descripción</h2>{description}{f'<ul class="features">{caracteristicas}</ul>' if caracteristicas else ''}</section>
<section class="panel"><p class="sobre">Antes de instalar</p><h2>Medidas publicadas</h2><dl class="datos medidas">{dimensiones}</dl><p class="nota">Confirma las medidas y el espacio de instalación antes de comprar.</p></section>
<section class="panel ancho"><p class="sobre">Datos por modelo</p><h2>Ficha técnica</h2><dl class="datos tabla">{especificaciones}</dl><p class="nota">Procedencia: {e(fuentes)}. Puede haber diferencias entre versiones del producto; confirma el modelo y la cobertura de garantía al comprar.</p></section></div>
<section class="cierre"><h2>¿Es el modelo que buscas?</h2><p>Indícanos el código <strong>{e(ref)}</strong> y te ayudaremos a confirmar detalles, precio y disponibilidad.</p><a class="primaria" href="tel:+56412907387">Consultar en tienda</a><a class="volver" href="../index.html">Volver al catálogo →</a></section></main>
<footer><span>Outlet Línea Blanca San Pedro · Local 38</span><a href="../index.html">Explorar catálogo</a></footer>
<div class="compare-bar" id="compareBar" hidden><span id="compareCount"></span><a href="../comparar.html" id="compareLink">Comparar modelos</a><button id="compareClear" type="button">Limpiar</button></div></body></html>'''


def main():
    feed = cargar("feed/catalogo_publico.json")
    raw = {normalizar_sku(p.get("ref")): p for p in cargar("productos.json")}
    oficiales = {normalizar_sku(k): v for k, v in cargar("fuentes_oficiales.json").items()}
    SALIDA.mkdir(exist_ok=True)
    DATOS.mkdir(parents=True, exist_ok=True)
    validos = set()
    for publico in feed:
        ref = normalizar_sku(publico["ref"])
        if not ref or publico.get("ficha") != f"p/{ref}.html":
            raise ValueError(f"Ruta insegura para {ref}")
        p = detalle(publico, raw.get(ref, {}), oficiales.get(ref, {}))
        (SALIDA / f"{ref}.html").write_text(ficha_html(p), encoding="utf-8")
        (DATOS / f"{ref}.json").write_text(json.dumps(p, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        validos.add(ref)
    for carpeta, sufijo in ((SALIDA, ".html"), (DATOS, ".json")):
        for archivo in carpeta.glob(f"*{sufijo}"):
            if archivo.stem not in validos:
                archivo.unlink()
    print(f"Fichas internas generadas: {len(validos)}")


if __name__ == "__main__":
    main()
