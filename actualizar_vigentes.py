#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actualiza el archivo interno de vigentes desde el Excel de San Pedro.

Uso:
    python actualizar_vigentes.py "San Pedro.xlsx"

No modifica el Excel y no agrega controles al catálogo público. Conserva por SKU
los campos internos verificados que ya existan en vigentes.json.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

RAIZ = Path(__file__).parent
SALIDA_PREDETERMINADA = RAIZ / "vigentes.json"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CAMPOS_BASE = {"sku", "descripcion", "unidad_negocio", "categoria", "subcategoria"}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", texto.upper()).strip()


def columna_numero(referencia):
    letras = re.match(r"[A-Z]+", referencia or "")
    numero = 0
    for letra in (letras.group(0) if letras else ""):
        numero = numero * 26 + ord(letra) - 64
    return numero


def texto_nodo(nodo):
    return "".join(t.text or "" for t in nodo.findall(f".//{{{NS}}}t"))


def leer_xlsx(ruta, hoja_preferida="STOCK"):
    with zipfile.ZipFile(ruta) as libro:
        compartidos = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz_shared = ET.fromstring(libro.read("xl/sharedStrings.xml"))
            compartidos = [texto_nodo(si) for si in raiz_shared.findall(f"{{{NS}}}si")]

        workbook = ET.fromstring(libro.read("xl/workbook.xml"))
        hojas = workbook.findall(f".//{{{NS}}}sheet")
        hoja = next(
            (h for h in hojas if str(h.get("name") or "").casefold() == hoja_preferida.casefold()),
            hojas[0] if hojas else None,
        )
        if hoja is None:
            raise RuntimeError("El archivo no contiene hojas.")

        relaciones = ET.fromstring(libro.read("xl/_rels/workbook.xml.rels"))
        destinos = {
            rel.get("Id"): rel.get("Target")
            for rel in relaciones.findall(f"{{{NS_PKG_REL}}}Relationship")
        }
        rel_id = hoja.get(f"{{{NS_REL}}}id")
        destino = destinos.get(rel_id, "")
        destino_limpio = destino.lstrip("/")
        archivo_hoja = (
            destino_limpio
            if destino_limpio.startswith("xl/")
            else str(PurePosixPath("xl") / PurePosixPath(destino_limpio))
        )
        if archivo_hoja not in libro.namelist():
            archivo_hoja = str(PurePosixPath("xl") / PurePosixPath(destino).name)
        xml_hoja = ET.fromstring(libro.read(archivo_hoja))

        filas = []
        for fila in xml_hoja.findall(f".//{{{NS}}}row"):
            valores = {}
            for celda in fila.findall(f"{{{NS}}}c"):
                columna = columna_numero(celda.get("r"))
                tipo = celda.get("t")
                valor = celda.find(f"{{{NS}}}v")
                if tipo == "s" and valor is not None and valor.text is not None:
                    indice = int(valor.text)
                    dato = compartidos[indice] if indice < len(compartidos) else ""
                elif tipo == "inlineStr":
                    dato = texto_nodo(celda)
                else:
                    dato = valor.text if valor is not None and valor.text is not None else ""
                valores[columna] = str(dato).strip()
            filas.append(valores)
    return str(hoja.get("name") or hoja_preferida), filas


def detectar_columnas(filas):
    alias = {
        "sku": {"SKU", "CODIGO", "CODIGO SAP"},
        "descripcion": {"DESCRIPCION", "NOMBRE", "NOMBRE PRODUCTO"},
        "unidad_negocio": {"UNEG", "UNIDAD DE NEGOCIO", "BUSINESS UNIT"},
        "categoria": {"CLASIF2", "CATEGORIA"},
        "subcategoria": {"CLASIF3", "SUBCATEGORIA"},
    }
    for posicion, fila in enumerate(filas):
        normalizadas = {col: normalizar(valor) for col, valor in fila.items()}
        columnas = {
            campo: next((col for col, valor in normalizadas.items() if valor in nombres), None)
            for campo, nombres in alias.items()
        }
        if columnas["sku"] and columnas["descripcion"]:
            return posicion, columnas
    raise RuntimeError("No se encontraron las columnas SKU y DESCRIPCION.")


def cargar_anteriores(ruta):
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(fila.get("sku") or "").strip().upper(): fila
        for fila in datos if isinstance(fila, dict) and fila.get("sku")
    }


def convertir(ruta_excel, salida, hoja):
    nombre_hoja, filas = leer_xlsx(ruta_excel, hoja)
    encabezado, columnas = detectar_columnas(filas)
    anteriores = cargar_anteriores(salida)
    resultado = []
    vistos = set()
    for fila in filas[encabezado + 1:]:
        sku = str(fila.get(columnas["sku"], "")).strip().upper()
        descripcion = str(fila.get(columnas["descripcion"], "")).strip()
        if not sku or not descripcion or sku in vistos:
            continue
        registro = {
            "sku": sku,
            "descripcion": descripcion,
            "unidad_negocio": str(fila.get(columnas.get("unidad_negocio"), "")).strip(),
            "categoria": str(fila.get(columnas.get("categoria"), "")).strip(),
            "subcategoria": str(fila.get(columnas.get("subcategoria"), "")).strip(),
        }
        for clave, valor in anteriores.get(sku, {}).items():
            if clave not in CAMPOS_BASE:
                registro[clave] = valor
        resultado.append(registro)
        vistos.add(sku)
    if not resultado:
        raise RuntimeError("No se encontraron productos vigentes válidos.")
    salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(resultado)} SKU importados desde la hoja {nombre_hoja} -> {salida.name}")


def main():
    parser = argparse.ArgumentParser(description="Actualiza vigentes.json desde el Excel de San Pedro.")
    parser.add_argument("archivo", type=Path, help="Ruta del archivo .xlsx")
    parser.add_argument("--hoja", default="STOCK", help="Hoja que contiene SKU y DESCRIPCION")
    parser.add_argument("--salida", type=Path, default=SALIDA_PREDETERMINADA)
    args = parser.parse_args()
    convertir(args.archivo.resolve(), args.salida.resolve(), args.hoja)


if __name__ == "__main__":
    main()
