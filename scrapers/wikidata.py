"""Identifica cada película en Wikidata (datos CC0, uso comercial permitido) para saber
cuándo dos cadenas nombran distinto la misma película.

Solo se usa el identificador (QID) para agrupar; el título que se muestra sigue siendo
el que publican los cines. Las búsquedas se guardan en app/www/data/wikidata.json,
así cada película se consulta una sola vez.
"""
import json
import time
from pathlib import Path

import requests

from comun import USER_AGENT, clave_pelicula, limpiar_titulo

API = "https://www.wikidata.org/w/api.php"
CACHE = Path(__file__).resolve().parents[1] / "app" / "www" / "data" / "wikidata.json"

# Tipos que cuentan como película: película, animada, documental, corto, de terror, etc.
TIPOS_PELICULA = {
    "Q11424", "Q202866", "Q93204", "Q24862", "Q506240", "Q24869", "Q229390",
    "Q20650540", "Q17123180", "Q1054574", "Q226730", "Q622548", "Q157394",
}


def _get(sesion, **params):
    params.update(format="json")
    r = sesion.get(API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _candidatos(sesion, consulta: str, idioma: str) -> list[str]:
    datos = _get(sesion, action="wbsearchentities", search=consulta, language=idioma,
                 uselang="es", type="item", limit=15)
    return [x["id"] for x in datos.get("search", [])]


def _anio(entidad) -> int:
    for c in entidad.get("claims", {}).get("P577", []):
        t = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("time", "")
        if t[1:5].isdigit():
            return int(t[1:5])
    return 0


def _nombres(entidad) -> set[str]:
    nombres = {v["value"] for v in entidad.get("labels", {}).values()}
    for lista in entidad.get("aliases", {}).values():
        nombres |= {v["value"] for v in lista}
    return {clave_pelicula(n) for n in nombres}


def buscar(sesion, titulo: str, original: str) -> str | None:
    """QID de la película cuyo nombre coincide exactamente; si hay varias, la más reciente."""
    consultas = [(original, "en"), (titulo, "es")] if original else [(titulo, "es")]
    for consulta, idioma in consultas:
        clave = clave_pelicula(limpiar_titulo(consulta))
        if not clave:
            continue
        ids = _candidatos(sesion, limpiar_titulo(consulta), idioma)
        if not ids:
            continue
        ents = _get(sesion, action="wbgetentities", ids="|".join(ids),
                    props="claims|labels|aliases", languages="es|en").get("entities", {})
        coinciden = [
            e for e in ents.values()
            if any(c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id") in TIPOS_PELICULA
                   for c in e.get("claims", {}).get("P31", []))
            and clave in _nombres(e)
        ]
        if coinciden:
            return max(coinciden, key=_anio)["id"]
        time.sleep(0.3)
    return None


def identificar(funciones: list[dict]) -> dict[str, str]:
    """Devuelve {título: QID} para las películas que se encuentren en Wikidata."""
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}

    peliculas = {}
    for f in funciones:
        if f.get("titulo_original") or f["pelicula"] not in peliculas:
            peliculas[f["pelicula"]] = f.get("titulo_original") or peliculas.get(f["pelicula"], "")

    sesion = requests.Session()
    sesion.headers["User-Agent"] = USER_AGENT
    nuevas = 0
    for titulo, original in peliculas.items():
        clave = clave_pelicula(titulo)
        if clave in cache:
            continue
        try:
            cache[clave] = buscar(sesion, titulo, original)
        except requests.RequestException as e:
            print(f"  wikidata: error con «{titulo}»: {e}")
            break   # sin conexión: se reintenta en la próxima corrida
        nuevas += 1
        time.sleep(0.3)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    resultado = {t: cache[clave_pelicula(t)] for t in peliculas if cache.get(clave_pelicula(t))}
    print(f"  wikidata: {len(resultado)}/{len(peliculas)} películas identificadas ({nuevas} búsquedas nuevas)")
    return resultado
