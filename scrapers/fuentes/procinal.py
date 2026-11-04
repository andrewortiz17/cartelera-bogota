"""Procinal Bogotá: página pública de cada teatro (www.procinal.com.co/ciudad/bogota/teatros/<teatro>).
Muestra HOY por defecto:
    GODZILLA MINUS ZERO / GODZILLA MINUS ZERO / Subtitulada - 2D / 6:30 pm / 9:10 pm / …
(ojo: procinal.com es otra empresa, Cineprox, que no opera en Bogotá)
"""
import re
import time

from comun import PAUSA_SEGUNDOS, Funcion, abrir, asignar_posters, imagenes_en_pagina, hora_a_24, hoy, iso, limpiar_lineas, titulo_bonito

NOMBRE = "procinal"
BASE = "https://www.procinal.com.co/ciudad/bogota/teatros/"
SALAS = {
    "bima": "pr-bima", "bulevar": "pr-bulevar", "suba": "pr-suba", "tunal": "pr-tunal",
    "imax": "pr-imax", "palatino": "pr-palatino", "americas": "pr-americas",
    "salitre": "pr-salitre", "tintal": "pr-tintal", "occidente": "pr-occidente",
}

RE_FORMATO = re.compile(r"^(Doblada|Subtitulada|Original|Español)\s*-\s*(.+)$", re.I)
RE_HORA = re.compile(r"^\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?$", re.I)


def parsear(texto: str, sala_id: str, url: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = limpiar_lineas(texto)
    out, titulo, original, idioma, formato = [], None, "", "", ""
    for i, l in enumerate(L):
        if (m := RE_FORMATO.match(l)):
            # Nueva película si lo anterior no era una hora (otro formato de la misma película)
            if i >= 2 and not RE_HORA.match(L[i - 1]):
                titulo, original = L[i - 2], L[i - 1]
            idioma, formato = m.group(1).capitalize(), m.group(2).upper()
        elif titulo and RE_HORA.match(l):
            hm = hora_a_24(l)
            if hm:
                out.append(Funcion(sala_id=sala_id, pelicula=titulo_bonito(titulo),
                                   titulo_original=titulo_bonito(original) if original != titulo else "",
                                   hora=iso(dia, hm), formato=formato, idioma=idioma,
                                   url_compra=url, fuente=NOMBRE))
        elif titulo and not RE_HORA.match(l) and not RE_FORMATO.match(L[i + 1] if i + 1 < len(L) else "") \
                and not (i + 2 < len(L) and RE_FORMATO.match(L[i + 2])):
            titulo = None   # fin de la cartelera (dirección, pie de página…)
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    funciones = []
    try:
        for slug, sala_id in SALAS.items():
            url = BASE + slug
            texto = abrir(pagina, url, esperar=r"(Doblada|Subtitulada|Original) - ", extra_ms=1500)
            nuevas = parsear(texto, sala_id, url)
            asignar_posters(nuevas, imagenes_en_pagina(pagina))
            print(f"  {NOMBRE}/{slug}: {len(nuevas)} funciones")
            funciones += nuevas
            time.sleep(PAUSA_SEGUNDOS)
    finally:
        pagina.close()
    return funciones
