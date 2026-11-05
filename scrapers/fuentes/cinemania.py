"""Cinemanía (Cra. 14 # 93A-85): publica la programación de la semana en su página principal:
    Programación del 05 al 11 de noviembre de 2026
    CABALLO SALVAJE NUEVE / 2:45 - 6:00 - 8:15 p.m / Ver más / …
Los mismos horarios valen para todos los días del rango.
"""
import re
from datetime import date, timedelta

from comun import MESES, Funcion, abrir, hora_a_24, hoy, iso, limpiar_lineas, sin_tildes, titulo_bonito

NOMBRE = "cinemania"
URL = "https://cinemania.com.co/"
SALA_ID = "ind-cinemania"

RE_RANGO = re.compile(r"Programaci[oó]n del (\d{1,2})(?: de (\w+))? al (\d{1,2}) de (\w+)(?: de (\d{4}))?", re.I)
RE_HORARIOS = re.compile(r"^\d{1,2}:\d{2}(\s*-\s*\d{1,2}:\d{2})*\s*([ap])\.?\s*m\.?$", re.I)


def _rango(texto: str, ref: date) -> tuple[date, date] | None:
    m = RE_RANGO.search(texto)
    if not m:
        return None
    d1, mes1, d2, mes2, anio = m.groups()
    mes2_n = MESES.get(sin_tildes(mes2.lower()))
    mes1_n = MESES.get(sin_tildes(mes1.lower())) if mes1 else mes2_n
    if not mes1_n or not mes2_n:
        return None
    a = int(anio) if anio else ref.year
    inicio = date(a if mes1_n <= mes2_n else a - 1, mes1_n, int(d1))
    return inicio, date(a, mes2_n, int(d2))


def parsear(texto: str, ref: date | None = None) -> list[Funcion]:
    ref = ref or hoy()
    rango = _rango(texto, ref)
    if not rango:
        return []
    inicio, fin = rango
    L = limpiar_lineas(texto)
    out = []
    for i, l in enumerate(L):
        m = RE_HORARIOS.match(l)
        if not m or i == 0:
            continue
        titulo = titulo_bonito(L[i - 1])
        sufijo = m.group(2).lower()
        horas = re.findall(r"\d{1,2}:\d{2}", l)
        dia = max(inicio, ref)
        # "11:30 - 2:00 - 5:00 p.m": una hora mayor que alguna posterior es de la mañana
        crudas = [int(h.split(":")[0]) for h in horas]
        horas_ok = []
        for k, h in enumerate(horas):
            manana = sufijo == "p" and crudas[k] != 12 and any(c < crudas[k] for c in crudas[k + 1:])
            horas_ok.append(hora_a_24(f"{h} {'a' if manana else sufijo}m"))
        while dia <= fin:
            for hm in horas_ok:
                if hm:
                    out.append(Funcion(sala_id=SALA_ID, pelicula=titulo, hora=iso(dia, hm),
                                       url_compra=URL, fuente=NOMBRE))
            dia += timedelta(days=1)
    return out


def _posters(pagina, funciones):
    """Las imágenes no tienen texto alternativo; van en el mismo orden que las películas."""
    try:
        srcs = pagina.eval_on_selector_all(
            'a[href*="/peliculas/"] img', "els => els.map(e => e.currentSrc || e.src)")
        enlaces = pagina.eval_on_selector_all(
            'a[href*="/peliculas/"] img', "els => els.map(e => e.closest('a').getAttribute('href'))")
    except Exception:
        return
    por_slug = dict(zip(enlaces, srcs))
    titulos = list(dict.fromkeys(f.pelicula for f in funciones))
    imagenes = list(dict.fromkeys(por_slug.values()))
    for t, src in zip(titulos, imagenes):
        for f in funciones:
            if f.pelicula == t:
                f.poster = src


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    try:
        funciones = parsear(abrir(pagina, URL, esperar="Programaci", extra_ms=1500))
        _posters(pagina, funciones)
    finally:
        pagina.close()
    print(f"  {NOMBRE}: {len(funciones)} funciones")
    return funciones
