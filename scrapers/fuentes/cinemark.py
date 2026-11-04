"""Cinemark: lee la página pública de cada teatro (www.cinemark.com.co/ciudad/bogota/<teatro>).

Por defecto muestra HOY. Cada película aparece así:
    CLAYFACE / VER DETALLE / TERROR+ 15 AÑOS110 MINUTOS / HORARIOS DISPONIBLES / … /
    2D / DOBLADA / Sillas: / GENERAL / 14:35 / 17:45 / …
"""
import re
import time

from comun import PAUSA_SEGUNDOS, Funcion, abrir, hora_a_24, hoy, iso, limpiar_lineas, titulo_bonito

NOMBRE = "cinemark"
BASE = "https://www.cinemark.com.co/ciudad/bogota/"

# slug → id en salas.json (todos confirmados el 4 nov 2026)
SALAS = {
    "plaza-imperial": "cm-plaza-imperial", "multiplaza": "cm-multiplaza",
    "micentro-el-porvenir": "cm-porvenir", "atlantis": "cm-atlantis", "floresta": "cm-floresta",
    "gran-plaza-bosa": "cm-gran-plaza-bosa", "gran-plaza-el-ensueno": "cm-ensueno",
    "parque-colina": "cm-colina",
}

RE_HORA = re.compile(r"^\d{1,2}:\d{2}$")
RE_INFO = re.compile(r"(\d+)\s*MINUTOS", re.I)
FORMATOS = {"2D", "3D", "XD", "DBOX", "D-BOX", "4D", "PREMIER", "IMAX"}
IDIOMAS = {"DOBLADA": "Doblada", "SUBTITULADA": "Subtitulada", "ESPAÑOL": "Español", "ORIGINAL": "Original"}


def parsear(texto: str, sala_id: str, url: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = [l for l in limpiar_lineas(texto) if l != "CARGANDO"]
    out = []
    titulo, dur, clasif, formato, idioma = None, None, "", "", ""
    for i, l in enumerate(L):
        if l == "VER DETALLE" and i > 0:
            titulo, formato, idioma = titulo_bonito(L[i - 1]), "", ""
            info = L[i + 1] if i + 1 < len(L) else ""
            m = RE_INFO.search(info)
            dur = int(m.group(1)) if m else None
            c = re.search(r"\+\s*\d+\s*AÑOS|TODOS", info, re.I)
            clasif = c.group(0).replace("+ ", "+") if c else ""
        elif titulo and l.upper() in FORMATOS:
            formato = l.upper()
        elif titulo and l.upper() in IDIOMAS:
            idioma = IDIOMAS[l.upper()]
        elif titulo and RE_HORA.match(l):
            hm = hora_a_24(l)
            if hm:
                out.append(Funcion(sala_id=sala_id, pelicula=titulo, hora=iso(dia, hm),
                                   formato=formato, idioma=idioma, clasificacion=clasif,
                                   duracion_min=dur, url_compra=url, fuente=NOMBRE))
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    funciones = []
    try:
        for slug, sala_id in SALAS.items():
            url = BASE + slug
            texto = abrir(pagina, url, esperar="HORARIOS DISPONIBLES", extra_ms=2500)
            nuevas = parsear(texto, sala_id, url)
            print(f"  {NOMBRE}/{slug}: {len(nuevas)} funciones")
            funciones += nuevas
            time.sleep(PAUSA_SEGUNDOS)
    finally:
        pagina.close()
    return funciones
