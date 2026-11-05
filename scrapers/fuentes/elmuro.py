"""Cine Club El Muro: su web usa The Events Calendar (WordPress), que publica los eventos
como datos en /wp-json/tribe/events/v1/events. No hace falta abrir el navegador:
una sola consulta trae título, fecha, sede, afiche y enlace de cada función.
"""
import html
from datetime import datetime

import requests

from comun import BOGOTA_TZ, USER_AGENT, Funcion, hoy, limpiar_titulo, sin_tildes, titulo_bonito

NOMBRE = "elmuro"
API = "https://cineclubelmuro.com/wp-json/tribe/events/v1/events"

# Sede (sin tildes, minúsculas, primeras palabras) → id en salas.json
SEDES = {
    "la tavola santa": "club-elmuro-tavola",
    "bogota coffee roasters": "club-elmuro-coffee",
}


def sede_de(nombre: str) -> str | None:
    clave = sin_tildes(html.unescape(nombre or "").lower())
    return next((v for k, v in SEDES.items() if clave.startswith(k)), None)


def convertir(eventos: list[dict]) -> list[Funcion]:
    out = []
    for e in eventos:
        sala = sede_de((e.get("venue") or {}).get("venue", ""))
        if not sala:
            print(f"  {NOMBRE}: sede sin registrar: {(e.get('venue') or {}).get('venue')!r}")
            continue
        inicio = datetime.strptime(e["start_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=BOGOTA_TZ)
        titulo = html.unescape(e.get("title", ""))
        # "LOS DEMONIOS (KEN RUSSELL'S FILM OF THE DEVILS)" → título y título original
        original = ""
        if titulo.endswith(")") and "(" in titulo:
            titulo, original = titulo[:-1].split("(", 1)
            titulo, original = titulo.strip(), original.strip()
        out.append(Funcion(
            sala_id=sala, pelicula=titulo_bonito(limpiar_titulo(titulo)),
            titulo_original=titulo_bonito(original), hora=inicio.isoformat(),
            formato="Cineclub", url_compra=e.get("url", ""), fuente=NOMBRE,
            poster=(e.get("image") or {}).get("url", "") if isinstance(e.get("image"), dict) else "",
        ))
    return out


def obtener(_navegador=None) -> list[Funcion]:
    r = requests.get(API, params={"per_page": 50, "start_date": hoy().isoformat()},
                     headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    funciones = convertir(r.json().get("events", []))
    print(f"  {NOMBRE}: {len(funciones)} funciones")
    return funciones
