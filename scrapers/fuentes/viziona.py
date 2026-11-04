"""Viziona Cines (C.C. El Edén): una sola sede; la página principal muestra HOY:
    CLAYFACE / Sala: VMAX / 2D / DOBLADA / 3:15 pm / 5:45 pm / Sala: VIP / 2D / DOBLADA / 6:55 pm / …
"""
import re

from comun import Funcion, abrir, hora_a_24, hoy, iso, limpiar_lineas, titulo_bonito

NOMBRE = "viziona"
URL = "https://vizionacines.com/"
SALA_ID = "vz-eden"

RE_HORA = re.compile(r"^\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?$", re.I)
IDIOMAS = {"DOBLADA": "Doblada", "SUBTITULADA": "Subtitulada", "ORIGINAL": "Original", "ESPAÑOL": "Español"}
FORMATOS = {"2D", "3D", "4D"}


def parsear(texto: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = limpiar_lineas(texto)
    out, titulo, sala, formato, idioma = [], None, "", "", ""
    for i, l in enumerate(L):
        if l.startswith("Sala:"):
            if i > 0 and not RE_HORA.match(L[i - 1]):
                titulo = L[i - 1]
            sala = l.split(":", 1)[1].strip()
        elif titulo and l.upper() in FORMATOS:
            formato = l.upper()
        elif titulo and l.upper() in IDIOMAS:
            idioma = IDIOMAS[l.upper()]
        elif titulo and RE_HORA.match(l):
            hm = hora_a_24(l)
            if hm:
                out.append(Funcion(sala_id=SALA_ID, pelicula=titulo_bonito(titulo), hora=iso(dia, hm),
                                   formato=f"{formato} {sala.title()}".strip(), idioma=idioma,
                                   url_compra=URL, fuente=NOMBRE))
    return out


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    try:
        funciones = parsear(abrir(pagina, URL, esperar="Sala:", extra_ms=2000))
    finally:
        pagina.close()
    print(f"  {NOMBRE}: {len(funciones)} funciones")
    return funciones
