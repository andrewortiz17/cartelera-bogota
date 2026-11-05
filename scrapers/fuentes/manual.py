"""Funciones escritas a mano en scrapers/manual.csv (cineclubes y salas sin web).

Se edita con Excel: una fila por función. Columnas:
    sala_id   id de la sala (ver la hoja salas-ids.csv; p. ej. club-unal)
    pelicula  título en español
    fecha     2026-11-20 o 20/11/2026
    hora      19:00 o 7:00 pm
    idioma, formato, url, poster, titulo_original   (opcionales)
Las filas con fecha pasada se ignoran solas, así que no hace falta borrarlas.
"""
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

from comun import Funcion, hora_a_24, hoy, iso

NOMBRE = "manual"
ARCHIVO = Path(__file__).resolve().parents[1] / "manual.csv"
SALAS = Path(__file__).resolve().parents[2] / "app" / "www" / "data" / "salas.json"


def leer_fecha(texto: str) -> date | None:
    t = texto.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(t, formato).date()
        except ValueError:
            pass
    return None


def leer_hora(texto: str):
    t = texto.strip().lower()
    if re.fullmatch(r"\d{1,2}\s*[ap]\.?\s*m\.?", t):      # "7 pm"
        t = re.sub(r"(\d+)", r"\1:00", t, count=1)
    return hora_a_24(t)


def filas(texto: str) -> list[dict]:
    primera = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primera.count(";") > primera.count(",") else ","   # Excel en español usa ;
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in fila.items()}
            for fila in csv.DictReader(texto.splitlines(), delimiter=separador)]


def convertir(registros: list[dict], salas_validas: set[str], desde: date) -> list[Funcion]:
    out = []
    for n, r in enumerate(registros, start=2):   # fila 1 = encabezados
        if not any(r.values()):
            continue
        sala, pelicula = r.get("sala_id", ""), r.get("pelicula", "")
        dia, hm = leer_fecha(r.get("fecha", "")), leer_hora(r.get("hora", ""))
        problema = ("sala_id desconocido" if salas_validas and sala not in salas_validas else
                    "falta la película" if not pelicula else
                    "fecha no válida" if not dia else
                    "hora no válida" if not hm else None)
        if problema:
            print(f"  {NOMBRE}: fila {n} ignorada ({problema}): {r}")
            continue
        if dia < desde:
            continue
        # iso() pasa al día siguiente las horas de madrugada; aquí la fecha escrita manda
        hora = datetime(dia.year, dia.month, dia.day, *hm).isoformat() + "-05:00"
        out.append(Funcion(sala_id=sala, pelicula=pelicula, hora=hora,
                           titulo_original=r.get("titulo_original", ""), formato=r.get("formato", ""),
                           idioma=r.get("idioma", ""), url_compra=r.get("url", ""),
                           fuente=NOMBRE, poster=r.get("poster", "")))
    return out


def obtener(navegador=None) -> list[Funcion]:
    if not ARCHIVO.exists():
        print(f"  {NOMBRE}: no existe {ARCHIVO.name}")
        return []
    texto = ARCHIVO.read_bytes().decode("utf-8-sig", errors="replace")
    try:
        datos = json.loads(SALAS.read_text(encoding="utf-8"))
        validas = {s["id"] for s in (datos["salas"] if isinstance(datos, dict) else datos)}
    except (OSError, KeyError, json.JSONDecodeError):
        validas = set()
    funciones = convertir(filas(texto), validas, hoy())
    print(f"  {NOMBRE}: {len(funciones)} funciones desde {ARCHIVO.name}")
    return funciones
