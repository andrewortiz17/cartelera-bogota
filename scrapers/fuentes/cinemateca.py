"""Cinemateca de Bogotá: agenda pública por sede (cinematecadebogota.gov.co/agenda/<sede>).
Muestra varios días seguidos:
    Estrenos Nacionales / KMKZ: SALVAJE, LIBRE Y VALIENTE / SALA CAPITAL / Noviembre 18 / 8:00 pm
"""
import re
import time
from datetime import date

from comun import MESES, PAUSA_SEGUNDOS, Funcion, abrir, asignar_posters, imagenes_en_pagina, hora_a_24, hoy, iso, limpiar_lineas, sin_tildes, titulo_bonito

NOMBRE = "cinemateca"
BASE = "https://cinematecadebogota.gov.co/agenda/"
SEDES = {11: "cine-cinemateca", 12: "cine-tunal", 80: "cine-fontanar", 112: "cine-cefe-chapinero"}

RE_FECHA = re.compile(r"^([A-Za-zé]+) (\d{1,2})$")
RE_HORA = re.compile(r"^\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?$", re.I)


def fecha(mes_txt: str, d: int, ref: date) -> date | None:
    mes = MESES.get(sin_tildes(mes_txt.lower()))
    if not mes:
        return None
    anio = ref.year + (1 if mes < ref.month - 1 else 0)   # diciembre → enero
    return date(anio, mes, d)


def parsear(texto: str, sala_id: str, url: str, ref=None) -> list[Funcion]:
    ref = ref or hoy()
    L = limpiar_lineas(texto)
    out = []
    for i, l in enumerate(L):
        m = RE_FECHA.match(l)
        if not m or i < 2 or i + 1 >= len(L) or not RE_HORA.match(L[i + 1]):
            continue
        dia = fecha(m.group(1), int(m.group(2)), ref)
        hm = hora_a_24(L[i + 1])
        if not dia or not hm or dia < ref:
            continue
        sala_txt = L[i - 1] if L[i - 1].upper().startswith("SALA") else ""
        titulo = L[i - 2] if sala_txt else L[i - 1]
        out.append(Funcion(sala_id=sala_id, pelicula=titulo_bonito(titulo), hora=iso(dia, hm),
                           formato=sala_txt.title(), url_compra=url, fuente=NOMBRE))
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    funciones = []
    try:
        for sede, sala_id in SEDES.items():
            url = f"{BASE}{sede}"
            nuevas = parsear(abrir(pagina, url, esperar=r"\d{1,2}:\d{2}\s*[ap]m", extra_ms=1000), sala_id, url)
            asignar_posters(nuevas, imagenes_en_pagina(pagina))
            print(f"  {NOMBRE}/{sede}: {len(nuevas)} funciones")
            funciones += nuevas
            time.sleep(PAUSA_SEGUNDOS)
    finally:
        pagina.close()
    return funciones
