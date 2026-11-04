"""Cinépolis: una sola página con los 4 complejos de Bogotá (programación de HOY):
    CINÉPOLIS VIP PLAZA CLARO / Clayface / A15108 min / DOB / 15:4018:20 / DIG / SUB / 21:20 / …
(las horas pueden venir pegadas, por eso se extraen con una expresión regular).
"""
import re

from comun import Funcion, abrir, asignar_posters, imagenes_en_pagina, hora_a_24, hoy, iso, limpiar_lineas, sin_tildes

NOMBRE = "cinepolis"
URL = "https://cinepolis.com.co/cartelera/bogota-colombia"

SALAS = {
    "cinepolis vip plaza claro": "cp-plaza-claro",
    "cinepolis diverplaza": "cp-diverplaza",
    "cinepolis mallplaza nqs": "cp-mallplaza-nqs",
    "cinepolis hayuelos colombia": "cp-hayuelos",
}

# Clasificación pegada a la duración: "A15108 min" = A15 + 108 min, "TP116 min" = TP + 116 min
RE_INFO = re.compile(r"^(A18|A15|A12|A7|AA|TP|A|B|C)(\d{2,3}) min$")
RE_HORAS = re.compile(r"\d{1,2}:\d{2}")
IDIOMAS = {"DOB": "Doblada", "SUB": "Subtitulada", "ESP": "Español", "ORI": "Original"}
FORMATOS = {"DIG": "2D", "2D": "2D", "3D": "3D", "4DX": "4DX", "IFV": "IFV", "VIP": "VIP",
            "MACRO XE": "Macro XE", "IFV XE": "IFV XE", "IFV 4DX": "IFV 4DX", "SJ": "Junior", "OV": "OV"}


def parsear(texto: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = limpiar_lineas(texto)
    out, sala, titulo, clasif, dur, formato, idioma = [], None, None, "", None, "2D", ""
    for i, l in enumerate(L):
        clave = sin_tildes(l.lower())
        if l.isupper() and clave in SALAS:
            sala, titulo = SALAS[clave], None
            continue
        if not sala:
            continue
        if (m := RE_INFO.match(l)) and i > 0:
            titulo, clasif, dur, formato, idioma = L[i - 1], m.group(1), int(m.group(2)), "2D", ""
        elif titulo and l.upper() in IDIOMAS:
            idioma = IDIOMAS[l.upper()]
        elif titulo and l.upper() in FORMATOS:
            formato = FORMATOS[l.upper()]
        elif titulo and re.fullmatch(r"(\d{1,2}:\d{2})+", l.replace(" ", "")):
            for h in RE_HORAS.findall(l):
                hm = hora_a_24(h)
                if hm:
                    out.append(Funcion(sala_id=sala, pelicula=titulo, hora=iso(dia, hm),
                                       formato=formato, idioma=idioma, clasificacion=clasif,
                                       duracion_min=dur, url_compra=URL, fuente=NOMBRE))
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    try:
        funciones = parsear(abrir(pagina, URL, esperar=r"\d{2,3} min", extra_ms=2500))
        asignar_posters(funciones, imagenes_en_pagina(pagina))
    finally:
        pagina.close()
    print(f"  {NOMBRE}: {len(funciones)} funciones")
    return funciones
