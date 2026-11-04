"""[NO SE USA en la cartelera; solo para pruebas] Pósters desde TMDB (themoviedb.org).
La cartelera usa los pósters que publica cada cine (ver comun.asignar_posters).

Necesita un token de lectura de TMDB (gratis): https://www.themoviedb.org/settings/api
→ "API Read Access Token". Guárdalo en scrapers/tmdb_token.txt (no se sube a GitHub)
o en la variable de entorno TMDB_TOKEN.

Los resultados se guardan en app/www/data/posters.json para no repetir búsquedas:
cada película se busca una sola vez.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests

from comun import clave_pelicula

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ.parent / "app" / "www" / "data" / "posters.json"
API = "https://api.themoviedb.org/3/search/movie"
IMAGEN = "https://image.tmdb.org/t/p/w342"


def token() -> str | None:
    archivo = RAIZ / "tmdb_token.txt"
    if archivo.exists():
        t = archivo.read_text(encoding="utf-8").strip()
        if t:
            return t
    return os.environ.get("TMDB_TOKEN") or None


def _buscar(sesion, consulta: str) -> list[dict]:
    r = sesion.get(API, params={"query": consulta, "language": "es-CO", "include_adult": "false"}, timeout=15)
    r.raise_for_status()
    return r.json().get("results", [])


def _elegir(resultados: list[dict]) -> dict | None:
    """Prefiere películas recientes (o reestrenos famosos) con póster y más populares."""
    anio = datetime.now().year
    con_poster = [r for r in resultados if r.get("poster_path")]
    if not con_poster:
        return None

    def puntaje(r):
        fecha = r.get("release_date") or "0000"
        reciente = 1 if fecha[:4].isdigit() and int(fecha[:4]) >= anio - 2 else 0
        return (reciente, r.get("popularity", 0))
    return max(con_poster[:8], key=puntaje)


def agregar(funciones: list[dict]) -> dict[str, dict]:
    """Devuelve {título en la app: {poster, tmdb_id, titulo_tmdb}} y actualiza la caché."""
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}

    peliculas = {}
    for f in funciones:
        peliculas.setdefault(f["pelicula"], f.get("titulo_original") or "")

    tk = token()
    if not tk:
        print("  posters: sin token de TMDB (scrapers/tmdb_token.txt); se usan solo los ya guardados")
    sesion = requests.Session()
    sesion.headers.update({"Authorization": f"Bearer {tk}", "accept": "application/json"})

    nuevos = 0
    for titulo, original in peliculas.items():
        clave = clave_pelicula(titulo)
        if clave in cache or not tk:
            continue
        elegido = None
        for consulta in [original, titulo, re.split(r"[:\-–(]", titulo)[0].strip()]:
            if not consulta:
                continue
            try:
                elegido = _elegir(_buscar(sesion, consulta))
            except requests.RequestException as e:
                print(f"  posters: error buscando «{consulta}»: {e}")
                break
            if elegido:
                break
        cache[clave] = {
            "titulo": titulo,
            "tmdb_id": elegido["id"] if elegido else None,
            "poster": IMAGEN + elegido["poster_path"] if elegido else None,
            "titulo_tmdb": elegido.get("title") if elegido else None,
        }
        nuevos += 1

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    resultado = {}
    for t in peliculas:
        d = cache.get(clave_pelicula(t))
        if d and d.get("tmdb_id"):
            resultado[t] = {"poster": d.get("poster"), "tmdb_id": d["tmdb_id"], "titulo_tmdb": d.get("titulo_tmdb")}
    con = sum(1 for d in resultado.values() if d["poster"])
    print(f"  posters: {con}/{len(peliculas)} películas con póster ({nuevos} búsquedas nuevas)")
    return resultado
