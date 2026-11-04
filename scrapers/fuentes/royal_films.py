"""Royal Films: la cartelera de Bogotá lista las películas; los horarios están en la
página de cada película, agrupados por día y por multicine:
    MIÉ / 04 nov / Multicine Paseo Villa Del Rio / 2D - ORI / 09:10 p. m. / …
"""
import re
import time

from comun import (MESES_CORTOS, PAUSA_SEGUNDOS, Funcion, hora_a_24, hoy, iso,
                   limpiar_lineas, sin_tildes, titulo_bonito)

NOMBRE = "royal_films"
BASE = "https://www.cinemasroyalfilms.com"
CARTELERA = BASE + "/cartelera/bogot%C3%A1"

# Nombre del multicine (sin tildes, minúsculas) → id en salas.json
SALAS = {
    "multicine paseo villa del rio": "rf-villa-del-rio",
    "multicine plaza de las americas": "rf-americas",
    "multicine milenio plaza": "rf-milenio",
    "multicine altavista": "rf-altavista",
    "multicine san rafael": "rf-san-rafael",
}

RE_DIA = re.compile(r"^(LUN|MAR|MI[EÉ]|JUE|VIE|S[AÁ]B|DOM)$", re.I)
RE_FECHA = re.compile(r"^(\d{1,2}) ([a-z]{3})$", re.I)
RE_HORA = re.compile(r"^\d{1,2}:\d{2}\s*[ap]\.\s*m\.$", re.I)
RE_FORMATO = re.compile(r"^(\w+)\s*-\s*(\w+)$")
IDIOMA = {"ORI": "Subtitulada", "DOB": "Doblada", "ESP": "Español"}


def sala_de(nombre: str) -> str | None:
    clave = sin_tildes(nombre.lower()).strip()
    if clave in SALAS:
        return SALAS[clave]
    return next((v for k, v in SALAS.items() if k in clave or clave in k), None)


def parsear(texto: str, url: str, dia=None) -> list[Funcion]:
    dia = dia or hoy()
    L = limpiar_lineas(texto)
    titulo = next((L[i + 1] for i, l in enumerate(L) if l.startswith("Inicio") and "/" in l and i + 1 < len(L)), "")
    original = next((l.split(":", 1)[1].strip() for l in L if l.startswith("Nombre original:")), "")
    clasif = next((l.split(":", 1)[1].strip() for l in L if l.startswith("Clasificación:")), "")
    dur = next((int(m.group(1)) for l in L if (m := re.match(r"^(\d+) mins?$", l))), None)
    out, en_hoy, sala, formato, idioma = [], False, None, "", ""
    for i, l in enumerate(L):
        if RE_DIA.match(l) and i + 1 < len(L) and (f := RE_FECHA.match(L[i + 1])):
            mes = MESES_CORTOS.get(sin_tildes(f.group(2).lower()))
            en_hoy = mes == dia.month and int(f.group(1)) == dia.day
            continue
        if l.upper().startswith("CARTELERA"):
            en_hoy = False
        if not en_hoy:
            continue
        if l.lower().startswith("multicine"):
            sala = sala_de(l)
            if sala is None:
                print(f"  {NOMBRE}: multicine sin registrar en SALAS: {l!r}")
        elif (m := RE_FORMATO.match(l)):
            formato, idioma = m.group(1).upper(), IDIOMA.get(m.group(2).upper(), m.group(2))
        elif RE_HORA.match(l) and sala:
            hm = hora_a_24(l)
            if hm:
                out.append(Funcion(sala_id=sala, pelicula=titulo_bonito(titulo),
                                   titulo_original=titulo_bonito(original), hora=iso(dia, hm),
                                   formato=formato, idioma=idioma, clasificacion=clasif,
                                   duracion_min=dur, url_compra=url, fuente=NOMBRE))
    return out


def elegir_bogota(pagina):
    """La web pide país y ciudad la primera vez."""
    pagina.goto(BASE, wait_until="networkidle", timeout=60000)
    if "Selecciona tu ubicación" not in pagina.inner_text("body"):
        return
    pagina.get_by_text("País", exact=True).first.click()
    pagina.get_by_role("listitem").filter(has_text="Colombia").first.click()
    pagina.wait_for_timeout(800)
    pagina.get_by_text("Ciudad", exact=True).first.click()
    pagina.get_by_role("listitem").filter(has_text="Bogotá").first.click()
    pagina.get_by_role("button", name="Seleccionar ubicación").click()
    pagina.wait_for_timeout(2500)


def obtener(navegador) -> list[Funcion]:
    pagina = navegador.new_page()
    funciones = []
    try:
        elegir_bogota(pagina)
        pagina.goto(CARTELERA, wait_until="networkidle", timeout=60000)
        pagina.wait_for_timeout(2500)
        enlaces = pagina.eval_on_selector_all(
            'a[href^="/pelicula/"]', "els => [...new Set(els.map(e => e.getAttribute('href')))]")
        print(f"  {NOMBRE}: {len(enlaces)} películas en la cartelera de Bogotá")
        for ruta in enlaces:
            url = BASE + ruta
            pagina.goto(url, wait_until="networkidle", timeout=60000)
            pagina.wait_for_timeout(2000)
            funciones += parsear(pagina.inner_text("body"), url)
            time.sleep(PAUSA_SEGUNDOS)
    finally:
        pagina.close()
    print(f"  {NOMBRE}: {len(funciones)} funciones")
    return funciones
