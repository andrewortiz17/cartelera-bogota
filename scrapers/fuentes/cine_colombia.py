"""Cine Colombia: lee la página pública de cada sala (www.cinecolombia.com/cinemas/<sala>/).

La página muestra por defecto la programación de HOY. Cada película aparece así:
    <título original> / <título en español> / <clasificación> / Duración / 2h 15m /
    Estreno: … / Género: … / Convenciones / [Todos los horarios:] / 12:40P.M. / SALA 3 / …
"""
import re
import time

from comun import PAUSA_SEGUNDOS, Funcion, abrir, asignar_posters, imagenes_en_pagina, hora_a_24, hoy, iso, limpiar_lineas

NOMBRE = "cine_colombia"
BASE = "https://www.cinecolombia.com/cinemas/"

# slug de la página → id en salas.json
SALAS = {
    "titan": "cc-titan", "centro-mayor": "cc-centro-mayor", "americas": "cc-americas",
    "andino": "cc-andino", "unicentro": "cc-unicentro", "santafe-bogota": "cc-santafe",
    "portal-80": "cc-portal-80", "plaza-central": "cc-plaza-central",
    "nuestro-bogota": "cc-nuestro-bogota", "metropolis": "cc-metropolis",
    "gran-estacion": "cc-gran-estacion", "galerias": "cc-galerias", "embajador": "cc-embajador",
    "cedritos": "cc-cedritos", "calle-100": "cc-calle-100", "avenida-chile": "cc-avenida-chile",
    "portoalegre": "cc-portoalegre", "lumina": "cc-lumina",
}

RE_CLASIF = re.compile(r"^(Recomendada para|Exclusiva para|Para todo el P[uú]blico|Sin clasificar|Apta para)", re.I)
RE_HORA = re.compile(r"^\d{1,2}:\d{2}\s*[AP]\.?\s*M\.?$", re.I)
RE_DUR = re.compile(r"^(\d+)h\s*(\d+)m$")
IGNORAR = {"Preventa", "Convenciones", "Todos los horarios:", "Duración"}


def parsear(texto: str, sala_id: str, url: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = limpiar_lineas(texto)
    idx = [i for i, l in enumerate(L) if RE_CLASIF.match(l)]
    out = []
    for n, i in enumerate(idx):
        titulo = L[i - 1]
        original = L[i - 2] if i >= 2 and L[i - 2] not in IGNORAR and not RE_HORA.match(L[i - 2]) \
            and not L[i - 2].upper().startswith(("SALA", "MEGASALA", "DINAMIX")) else ""
        fin = (idx[n + 1] - 2) if n + 1 < len(idx) else len(L)
        dur = None
        for j in range(i, fin):
            l = L[j]
            m = RE_DUR.match(l)
            if m:
                dur = int(m.group(1)) * 60 + int(m.group(2))
            if RE_HORA.match(l):
                hm = hora_a_24(l)
                sala = L[j + 1] if j + 1 < len(L) and not RE_HORA.match(L[j + 1]) else ""
                if hm:
                    out.append(Funcion(
                        sala_id=sala_id, pelicula=titulo,
                        titulo_original=original if original != titulo else "",
                        hora=iso(dia, hm), formato=sala.title() if sala else "",
                        clasificacion=L[i], duracion_min=dur, url_compra=url, fuente=NOMBRE))
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    funciones = []
    try:
        for slug, sala_id in SALAS.items():
            url = BASE + slug + "/"
            texto = abrir(pagina, url, esperar=r"\d{1,2}:\d{2}\s*[AP]\.?M", extra_ms=2000)
            nuevas = parsear(texto, sala_id, url)
            asignar_posters(nuevas, imagenes_en_pagina(pagina))
            print(f"  {NOMBRE}/{slug}: {len(nuevas)} funciones")
            funciones += nuevas
            time.sleep(PAUSA_SEGUNDOS)
    finally:
        pagina.close()
    return funciones
