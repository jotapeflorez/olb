#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse, csv, html, json, re, time, unicodedata
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

VERSION = "1.0.1"

FUENTES_PREDETERMINADAS = [
    "https://www.shopclub.cl",
    "https://www.totem.shopclub.cl",
    "https://www.electrolux.cl",
    "https://www.tiendamademsa.cl",
    "https://www.fensa.cl",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0 Safari/537.36 ExtractorOLB/1.0"
)

def log(msg):
    print(msg, flush=True)

def normalizar(txt):
    if txt is None:
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "", txt.upper())

def safe_name(txt, maxlen=120):
    txt = unquote(str(txt or "archivo"))
    txt = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", txt)
    txt = re.sub(r"\s+", " ", txt).strip(" ._")
    return (txt[:maxlen] or "archivo")

def http_get(url, timeout=25, retries=2):
    last = None
    for intento in range(retries + 1):
        try:
            req = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            })
            with urlopen(req, timeout=timeout) as r:
                return r.read(), r.geturl(), dict(r.headers.items())
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            last = e
            if intento < retries:
                time.sleep(1.2 * (intento + 1))
    raise RuntimeError(f"No se pudo abrir {url}: {last}")

def http_json(url):
    data, _, _ = http_get(url)
    return json.loads(data.decode("utf-8", errors="replace"))

def text_get(url):
    data, final_url, _ = http_get(url)
    return data.decode("utf-8", errors="replace"), final_url

def quitar_resize_vtex(url):
    if not url:
        return url
    u = html.unescape(url).replace("\\/", "/")
    u = re.sub(r"(/arquivos/ids/\d+)-\d+-\d+(?=/|\?|$)", r"\1", u)
    return u.split("?", 1)[0]

def image_id_from_url(url):
    m = re.search(r"/arquivos/ids/(\d+)", url or "")
    return m.group(1) if m else ""

def referencias_item(item):
    refs = []
    for r in item.get("referenceId") or []:
        if isinstance(r, dict):
            v = r.get("Value") or r.get("value")
            if v:
                refs.append(str(v))
    for k in ("itemId", "ean", "name", "nameComplete"):
        if item.get(k):
            refs.append(str(item[k]))
    return refs

def referencias_producto(prod):
    refs = []
    for k in ("productReference", "productId", "productName", "linkText"):
        if prod.get(k):
            refs.append(str(prod[k]))
    for item in prod.get("items") or []:
        refs.extend(referencias_item(item))
    return refs

def puntaje_producto(prod, consulta):
    q = normalizar(consulta)
    if not q:
        return 0
    score = 0
    for ref in referencias_producto(prod):
        n = normalizar(ref)
        if not n:
            continue
        if n == q:
            score = max(score, 100)
        elif q in n:
            score = max(score, 70)
        elif n in q and len(n) >= 5:
            score = max(score, 50)
    return score

def buscar_en_vtex(base, consulta):
    endpoints = [
        f"{base.rstrip('/')}/api/catalog_system/pub/products/search/{quote(consulta)}",
        f"{base.rstrip('/')}/api/catalog_system/pub/products/search?ft={quote(consulta)}",
    ]
    vistos = set()
    resultados = []
    for ep in endpoints:
        try:
            data = http_json(ep)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for p in data:
            pid = str(p.get("productId", "")) + "|" + str(p.get("linkText", ""))
            if pid not in vistos:
                vistos.add(pid)
                resultados.append(p)
        if resultados:
            break
    return resultados

def elegir_producto(productos, consulta):
    if not productos:
        return None, 0
    ranked = sorted(
        ((puntaje_producto(p, consulta), p) for p in productos),
        key=lambda x: x[0],
        reverse=True
    )
    return ranked[0][1], ranked[0][0]

def obtener_url_ficha(base, prod):
    link = prod.get("link")
    if link:
        if str(link).startswith("http"):
            return str(link)
        return urljoin(base.rstrip("/") + "/", str(link).lstrip("/"))
    lt = prod.get("linkText")
    if lt:
        return f"{base.rstrip('/')}/{lt}/p"
    return ""

def extraer_imagenes(prod):
    salida, vistos = [], set()
    for item in prod.get("items") or []:
        item_id = str(item.get("itemId", ""))
        item_name = item.get("nameComplete") or item.get("name") or ""
        for pos, img in enumerate(item.get("images") or [], start=1):
            url = img.get("imageUrl") or img.get("url") or ""
            if not url:
                continue
            original = quitar_resize_vtex(url)
            if original in vistos:
                continue
            vistos.add(original)
            label = img.get("imageLabel") or img.get("label") or ""
            text = img.get("imageText") or img.get("text") or ""
            iid = img.get("imageId") or image_id_from_url(url)
            descriptor = label or text or f"imagen_{pos:02d}"
            salida.append({
                "item_id": item_id,
                "item_name": item_name,
                "orden": pos,
                "image_id": iid,
                "label": label,
                "texto": text,
                "url_vtex": url,
                "url_original": original,
                "nombre_sugerido": safe_name(f"{pos:02d}_{descriptor}"),
            })
    return salida

def extraer_pdfs_de_html(page_html, page_url):
    encontrados, vistos = [], set()
    texto = html.unescape(page_html).replace("\\/", "/")
    patrones = [
        r'https?://[^"\'<>\s]+?\.pdf(?:\?[^"\'<>\s]*)?',
        r'//[^"\'<>\s]+?\.pdf(?:\?[^"\'<>\s]*)?',
        r'/[^"\'<>\s]+?\.pdf(?:\?[^"\'<>\s]*)?',
    ]
    for patron in patrones:
        for raw in re.findall(patron, texto, flags=re.I):
            if raw.startswith("//"):
                raw = "https:" + raw
            url = urljoin(page_url, raw)
            url = url.replace("\\u002F", "/")
            if url in vistos:
                continue
            vistos.add(url)
            name = Path(urlparse(url).path).name or "documento.pdf"
            encontrados.append({
                "nombre": safe_name(name),
                "url": url,
                "origen": "HTML ficha pública",
            })
    return encontrados

def extension_por_headers(url, headers):
    ct = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if "jpeg" in ct:
        return ".jpg"
    if "png" in ct:
        return ".png"
    if "webp" in ct:
        return ".webp"
    if "gif" in ct:
        return ".gif"
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ".jpg"

def cargar_consultas(args):
    vals = list(args.consultas or [])
    if args.archivo:
        p = Path(args.archivo)
        if not p.exists():
            raise SystemExit(f"No existe: {p}")
        if p.suffix.lower() == ".csv":
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.reader(f):
                    for cell in row:
                        if cell.strip():
                            vals.append(cell.strip())
                            break
        else:
            vals.extend(
                x.strip()
                for x in p.read_text(encoding="utf-8-sig").splitlines()
                if x.strip()
            )
    out, seen = [], set()
    for v in vals:
        k = normalizar(v)
        if k and k not in seen:
            seen.add(k)
            out.append(v.strip())
    return out

def escribir_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def procesar_modelo(consulta, fuentes, out_root, do_download):
    log(f"\n=== {consulta} ===")
    mejor, mejor_score, mejor_base = None, -1, ""
    candidatos_info = []

    for base in fuentes:
        log(f"Buscando en {base} ...")
        try:
            productos = buscar_en_vtex(base, consulta)
            prod, score = elegir_producto(productos, consulta)
            candidatos_info.append({"fuente": base, "resultados": len(productos), "score": score})
            if prod and score > mejor_score:
                mejor, mejor_score, mejor_base = prod, score, base
            if score >= 100:
                break
        except Exception as e:
            candidatos_info.append({"fuente": base, "error": str(e)})

    if not mejor:
        log("NO ENCONTRADO")
        return {
            "consulta": consulta, "estado": "NO ENCONTRADO", "fuente": "",
            "marca": "", "producto": "", "sap_referencia": "", "imagenes": 0,
            "pdfs": 0, "score_match": 0, "url_ficha": "", "error": ""
        }

    ficha = obtener_url_ficha(mejor_base, mejor)
    imgs = extraer_imagenes(mejor)
    refs = referencias_producto(mejor)
    product_ref = str(mejor.get("productReference", ""))
    numeric_refs = [r for r in refs if re.fullmatch(r"\d{7,14}", r.strip())]
    sap = product_ref if re.fullmatch(r"\d{7,14}", product_ref.strip()) else (numeric_refs[0] if numeric_refs else product_ref)

    carpeta = out_root / safe_name(normalizar(consulta) or consulta)
    carpeta.mkdir(parents=True, exist_ok=True)

    pdfs = []
    if ficha:
        try:
            page_html, final_page = text_get(ficha)
            pdfs = extraer_pdfs_de_html(page_html, final_page)
            ficha = final_page
        except Exception as e:
            log(f"  Aviso: no pude leer HTML de ficha para PDFs: {e}")

    producto_json = {
        "extractor_olb_version": VERSION,
        "consulta": consulta,
        "estado": "VERIFICADO" if mejor_score >= 70 else "REVISAR MATCH",
        "score_match": mejor_score,
        "fuente": mejor_base,
        "url_ficha": ficha,
        "productId": mejor.get("productId"),
        "productName": mejor.get("productName"),
        "productReference": product_ref,
        "sap_referencia_detectada": sap,
        "brand": mejor.get("brand"),
        "linkText": mejor.get("linkText"),
        "categorias": mejor.get("categories") or [],
        "referencias_detectadas": refs,
        "candidatos_fuentes": candidatos_info,
        "cantidad_imagenes": len(imgs),
        "cantidad_pdfs": len(pdfs),
    }
    (carpeta / "producto.json").write_text(
        json.dumps(producto_json, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    escribir_csv(
        carpeta / "imagenes.csv",
        imgs,
        ["orden","item_id","item_name","image_id","label","texto","url_vtex","url_original","nombre_sugerido"]
    )
    escribir_csv(carpeta / "documentos.csv", pdfs, ["nombre","url","origen"])

    if do_download:
        img_dir = carpeta / "imagenes"
        doc_dir = carpeta / "documentos"
        img_dir.mkdir(exist_ok=True)
        doc_dir.mkdir(exist_ok=True)

        for i, img in enumerate(imgs, start=1):
            urls = [img["url_original"]]
            if img["url_vtex"] != img["url_original"]:
                urls.append(img["url_vtex"])
            ok, last = False, ""
            for candidate in urls:
                try:
                    data, final_url, headers = http_get(candidate, timeout=40, retries=1)
                    ext = extension_por_headers(final_url, headers)
                    label = img["label"] or img["texto"] or f"imagen_{i:02d}"
                    name = safe_name(f"{i:02d}_{label}") + ext
                    (img_dir / name).write_bytes(data)
                    log(f"  ✓ imagen {i:02d}: {name}")
                    ok = True
                    break
                except Exception as e:
                    last = str(e)
            if not ok:
                log(f"  ✗ imagen {i:02d}: {last}")

        for i, doc in enumerate(pdfs, start=1):
            name = safe_name(doc["nombre"])
            if not name.lower().endswith(".pdf"):
                name += ".pdf"
            try:
                data, _, _ = http_get(doc["url"], timeout=40, retries=1)
                (doc_dir / f"{i:02d}_{name}").write_bytes(data)
                log(f"  ✓ PDF {i:02d}: {name}")
            except Exception as e:
                log(f"  ✗ PDF {i:02d}: {e}")

    log(f"Encontrado: {mejor.get('productName','')}")
    log(f"Referencia/SAP: {sap or '—'}")
    log(f"Imágenes: {len(imgs)} | PDFs detectados: {len(pdfs)}")
    log(f"Ficha: {ficha or '—'}")

    return {
        "consulta": consulta,
        "estado": producto_json["estado"],
        "fuente": mejor_base,
        "marca": mejor.get("brand", ""),
        "producto": mejor.get("productName", ""),
        "sap_referencia": sap,
        "imagenes": len(imgs),
        "pdfs": len(pdfs),
        "score_match": mejor_score,
        "url_ficha": ficha,
        "error": ""
    }

def main():
    ap = argparse.ArgumentParser(
        description="Extractor OLB v1 — recursos públicos oficiales de productos VTEX"
    )
    ap.add_argument("consultas", nargs="*", help="Modelos, SAP o referencias")
    ap.add_argument("--archivo", help="TXT o CSV con un modelo/SAP por fila")
    ap.add_argument("--salida", default="salida_olb", help="Carpeta de salida")
    ap.add_argument("--descargar", action="store_true", help="Descarga imágenes y PDFs")
    ap.add_argument("--fuente", action="append", help="Agregar/priorizar fuente VTEX")
    ap.add_argument("--version", action="version", version=f"Extractor OLB {VERSION}")
    args = ap.parse_args()

    consultas = cargar_consultas(args)
    if not consultas:
        ap.error("Indica al menos un modelo/SAP o usa --archivo.")

    fuentes = []
    if args.fuente:
        fuentes.extend([x.rstrip("/") for x in args.fuente])
    for f in FUENTES_PREDETERMINADAS:
        if f not in fuentes:
            fuentes.append(f)

    out_root = Path(args.salida)
    out_root.mkdir(parents=True, exist_ok=True)
    resumen = []

    for c in consultas:
        try:
            resumen.append(procesar_modelo(c, fuentes, out_root, args.descargar))
        except Exception as e:
            log(f"ERROR GENERAL en {c}: {e}")
            resumen.append({
                "consulta": c, "estado": "ERROR", "fuente": "", "marca": "",
                "producto": "", "sap_referencia": "", "imagenes": 0, "pdfs": 0,
                "score_match": 0, "url_ficha": "", "error": str(e)
            })

    fields = [
        "consulta","estado","fuente","marca","producto","sap_referencia",
        "imagenes","pdfs","score_match","url_ficha","error"
    ]
    escribir_csv(out_root / "resumen.csv", resumen, fields)

    log("\n=== FIN ===")
    log(f"Resumen: {out_root / 'resumen.csv'}")
    ok = sum(1 for r in resumen if r.get("estado") in ("VERIFICADO", "REVISAR MATCH"))
    log(f"Procesados: {len(resumen)} | Encontrados: {ok}")

if __name__ == "__main__":
    main()
